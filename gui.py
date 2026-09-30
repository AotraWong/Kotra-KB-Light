#!/usr/bin/env python3
"""KDE-friendly Qt 6 keyboard backlight editor."""
import math
import os
import subprocess
from pathlib import Path
import sys
import time
from PySide6.QtCore import Qt, QTimer, QPointF, QLockFile, QStandardPaths, QProcess
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QCheckBox, QTableWidget, QTableWidgetItem,
    QDoubleSpinBox, QSpinBox, QSlider, QFileDialog, QMessageBox, QHeaderView,
    QGroupBox, QSplitter, QSystemTrayIcon, QMenu, QButtonGroup, QWidgetAction, QFormLayout)
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from curve import load, save, validate, value_at, PRESET
from kbd_auto import Controller, sensor_path, number
from activity import ActivityEnvelope


class Hardware:
    def __init__(self):
        self.sensor = sensor_path()
        self.led = Path('/sys/class/leds/kbd_backlight')
        self.maximum = int(number(self.led / 'max_brightness'))
        if self.maximum <= 0:
            raise ValueError('无效的最大亮度')
        self.interface = None

    def read(self):
        return number(self.sensor), int(number(self.led / 'brightness'))

    def write(self, value):
        if not 0 <= value <= self.maximum:
            raise ValueError('亮度超出范围')
        if self.interface is None:
            self.interface = QDBusInterface('org.freedesktop.UPower',
                '/org/freedesktop/UPower/KbdBacklight',
                'org.freedesktop.UPower.KbdBacklight', QDBusConnection.systemBus())
            self.interface.setTimeout(1500)
        if not self.interface.isValid():
            self.interface = None
            raise RuntimeError('无法连接 UPower 键盘灯接口，请在本机桌面会话运行')
        reply = self.interface.call('SetBrightness', int(value))
        if reply.type() == QDBusMessage.MessageType.ErrorMessage:
            raise RuntimeError(f'UPower 调光失败：{reply.errorMessage()}')


class CurvePlot(QWidget):
    def __init__(self):
        super().__init__()
        self.data = load()
        self.lux = None
        self.setMinimumSize(360, 230)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.palette().text().color()
        accent = self.palette().highlight().color()
        left, top, w, h = 48, 25, self.width() - 75, self.height() - 70
        limit = max(300, self.data['bands'][-1]['lux'] * 1.2)
        # log1p axis keeps 0–2 lux and bright-room bands readable together.
        def x(lux):
            return left + math.log1p(min(lux, limit)) / math.log1p(limit) * w
        def y(brightness):
            return top + h * (1 - brightness / 255)
        p.setPen(color)
        p.drawText(left, 16, '键盘亮度 / 255')
        p.drawText(left, self.height() - 7, '环境光 lux（对数刻度；阶梯配置）')
        for value in (0, 64, 128, 192, 255):
            p.setPen(QPen(self.palette().mid().color(), 1))
            p.drawLine(QPointF(left, y(value)), QPointF(left + w, y(value)))
            p.setPen(color)
            p.drawText(5, int(y(value)) + 5, str(value))
        for lux in (0, 2, 10, 30, 80, 150, 300):
            if lux <= limit:
                p.drawText(int(x(lux)) - 8, int(top + h + 20), str(lux))
        path = QPainterPath()
        bands = self.data['bands']
        path.moveTo(x(0), y(bands[0]['brightness']))
        for i, band in enumerate(bands):
            if i:
                path.lineTo(x(band['lux']), y(bands[i-1]['brightness']))
                path.lineTo(x(band['lux']), y(band['brightness']))
        path.lineTo(x(limit), y(bands[-1]['brightness']))
        p.setPen(QPen(accent, 3))
        p.drawPath(path)
        if self.lux is not None:
            p.setPen(QPen(color, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x(self.lux), top), QPointF(x(self.lux), top + h))
            p.setBrush(accent)
            p.drawEllipse(QPointF(x(self.lux), y(value_at(self.data, self.lux))), 5, 5)


class Window(QMainWindow):
    def __init__(self, hardware=None):
        super().__init__()
        self.setWindowTitle('Kotra-KB-Light')
        self.setWindowIcon(QIcon(str(Path(__file__).with_name('keyboard.svg'))))
        self.resize(940, 690)
        self.tray = None
        self.exiting = False
        self.active_mode = None
        self.hardware = hardware
        self.data = load()
        self.dirty = False
        self.controller = None
        self.initial = None
        self.last_write = None
        self.last_time = time.monotonic()
        self.loading = False
        self.envelope = ActivityEnvelope()
        self.key_ready = False
        self.key_buffer = b''
        self.keys = QProcess(self)
        self.keys.readyReadStandardOutput.connect(self.key_output)
        self.keys.finished.connect(self.key_stopped)
        self.keys.errorOccurred.connect(self.key_error)
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)
        title = QLabel('Kotra-KB-Light')
        title.setStyleSheet('font-size: 23px; font-weight: 600;')
        layout.addWidget(title)
        self.readings = QLabel('正在读取环境光…')
        layout.addWidget(self.readings)
        row = QHBoxLayout()
        for label, callback in [('载入倒 U 预设', self.preset), ('打开配置…', self.open_config), ('保存配置…', self.save_config)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            row.addWidget(button)
        self.filename = QLabel('倒 U 预设')
        row.addWidget(self.filename, 1)
        layout.addLayout(row)
        split = QSplitter()
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['起始环境光（lux）', '键盘亮度（0–255）'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumWidth(330)
        self.table.itemChanged.connect(self.edited)
        split.addWidget(self.table)
        self.plot = CurvePlot()
        split.addWidget(self.plot)
        layout.addWidget(split, 1)
        row = QHBoxLayout()
        for label, callback in [('添加档位', self.add_band), ('删除所选档位', self.remove_band)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            row.addWidget(button)
        self.shift_button = QPushButton('换档配置')
        self.shift_menu = QMenu(self.shift_button)
        settings = QWidget()
        settings_layout = QFormLayout(settings)
        settings_layout.setContentsMargins(12, 10, 12, 10)
        self.hysteresis = QSpinBox()
        self.hysteresis.setRange(0, 50)
        self.hysteresis.setSuffix('%')
        self.hysteresis.setToolTip('环境光需超出档位边界的比例，用于避免反复切换。')
        settings_layout.addRow('切换幅度', self.hysteresis)
        self.settle = QDoubleSpinBox()
        self.settle.setRange(0, 60)
        self.settle.setSuffix(' 秒')
        settings_layout.addRow('持续时间', self.settle)
        settings_action = QWidgetAction(self.shift_menu)
        settings_action.setDefaultWidget(settings)
        self.shift_menu.addAction(settings_action)
        self.shift_button.setMenu(self.shift_menu)
        row.addWidget(self.shift_button)
        self.hysteresis.valueChanged.connect(self.edited)
        self.settle.valueChanged.connect(self.edited)
        layout.addLayout(row)
        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel('曲线查询'))
        self.query = QDoubleSpinBox()
        self.query.setRange(0, 1000000)
        self.query.setSuffix(' lux')
        self.query.setValue(120)
        self.query.valueChanged.connect(self.update_query)
        preview_row.addWidget(self.query)
        self.query_result = QLabel()
        preview_row.addWidget(self.query_result, 1)
        layout.addLayout(preview_row)
        group = QGroupBox('运行控制')
        controls = QVBoxLayout(group)
        row = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.mode_auto = QPushButton('自动调节')
        self.mode_always = QPushButton('常亮')
        for button, mode in [(self.mode_auto, 'auto'), (self.mode_always, 'always')]:
            button.setCheckable(True)
            self.mode_group.addButton(button)
            button.clicked.connect(lambda _checked, m=mode: self.select_mode(m))
            row.addWidget(button)
        row.addStretch()
        controls.addLayout(row)
        row = QHBoxLayout()
        self.key_status = QLabel('按键模式：需要授权；不读取到界面的具体键值')
        row.addWidget(self.key_status, 1)
        controls.addLayout(row)
        controls.addWidget(QLabel('按键立即亮起 → 保持 1 秒 → 渐暗 4 秒 → 熄灭；再次按键重新计时。'))
        row = QHBoxLayout()
        row.addWidget(QLabel('手动亮度'))
        self.manual = QSlider(Qt.Orientation.Horizontal)
        self.manual.setRange(0, 255)
        self.manual.setValue(64)
        self.manual_label = QLabel()
        self.manual.valueChanged.connect(lambda v: self.manual_label.setText(f'{v}/255 · {v/255:.0%}'))
        self.manual.valueChanged.emit(64)
        row.addWidget(self.manual, 1)
        row.addWidget(self.manual_label)
        apply = QPushButton('应用手动亮度')
        apply.clicked.connect(self.apply_manual)
        row.addWidget(apply)
        controls.addLayout(row)
        controls.addWidget(QLabel('手动应用会停止自动调节；关闭窗口会尝试恢复接管前亮度。'))
        layout.addWidget(group)
        self.status = QLabel('尚未接管灯光；请选择自动调节或常亮。')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.fill(self.data)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)
        self.tick()

    def fill(self, data):
        self.loading = True
        self.table.setRowCount(len(data['bands']))
        for row, band in enumerate(data['bands']):
            for col, key in enumerate(('lux', 'brightness')):
                self.table.setItem(row, col, QTableWidgetItem(str(band[key])))
        self.hysteresis.setValue(round(data['hysteresis'] * 100))
        self.settle.setValue(data['settle_seconds'])
        self.loading = False
        self.data = data
        self.plot.data = data
        self.plot.update()
        self.controller = None
        self.update_query()

    def edited(self, *_):
        if self.loading:
            return
        self.dirty = True
        self.pause_control()
        try:
            data = {'version': 1, 'name': '自定义曲线', 'hysteresis': self.hysteresis.value()/100,
                    'settle_seconds': self.settle.value(), 'bands': []}
            for row in range(self.table.rowCount()):
                data['bands'].append({'lux': float(self.table.item(row, 0).text()),
                                      'brightness': int(self.table.item(row, 1).text())})
            self.data = validate(data)
            self.plot.data = self.data
            self.plot.update()
            self.set_modes_enabled(True)
            self.status.setText('修改已用于预览；尚未保存。可重新开启自动调节。')
            self.controller = None
            self.update_query()
        except (ValueError, AttributeError, KeyError, TypeError) as exc:
            self.set_modes_enabled(False)
            self.status.setText(f'配置无效：{exc}；曲线图保留上一个有效配置。')

    def update_query(self, *_):
        value = value_at(self.data, self.query.value())
        self.query_result.setText(f'→ {value}/255（{value/255:.0%}），未计入换档配置和延迟')

    def discard(self):
        return not self.dirty or QMessageBox.question(self, '未保存的修改', '放弃未保存的曲线修改？') == QMessageBox.StandardButton.Yes

    def preset(self):
        if self.discard():
            self.pause_control()
            self.fill(load())
            self.set_modes_enabled(True)
            self.dirty = False
            self.filename.setText('倒 U 预设')
            self.status.setText('已载入倒 U 预设')

    def open_config(self):
        if not self.discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, '打开曲线', str(PRESET.parent), 'JSON (*.json)')
        if path:
            try:
                data = load(path)
                self.pause_control()
                self.fill(data)
                self.set_modes_enabled(True)
                self.filename.setText(Path(path).name)
                self.dirty = False
            except (OSError, ValueError, KeyError, TypeError) as exc:
                QMessageBox.warning(self, '打开失败', str(exc))

    def save_config(self):
        if not self.mode_auto.isEnabled():
            QMessageBox.warning(self, '无法保存', '请先修正无效档位。')
            return
        path, _ = QFileDialog.getSaveFileName(self, '保存曲线', str(Path(__file__).parent/'custom.json'), 'JSON (*.json)')
        if path:
            try:
                if Path(path).resolve() == PRESET.resolve():
                    raise ValueError('请另存为自定义配置，保留内置预设。')
                save(path, self.data)
                self.filename.setText(Path(path).name)
                self.dirty = False
                self.status.setText('配置已保存')
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, '保存失败', str(exc))

    def add_band(self):
        if not self.mode_auto.isEnabled():
            return
        data = dict(self.data, bands=self.data['bands'] + [{'lux': self.data['bands'][-1]['lux'] + 100, 'brightness': 0}])
        self.fill(data)
        self.edited()

    def remove_band(self):
        row = self.table.currentRow()
        if row <= 0 or self.table.rowCount() <= 2:
            self.status.setText('保留 0 lux 起始档位，且至少需要两个档位。')
            return
        self.table.removeRow(row)
        self.edited()

    def restore(self):
        if self.hardware and self.last_write is not None:
            try:
                _, current = self.hardware.read()
                if current == self.last_write:
                    self.hardware.write(self.initial)
            except Exception as exc:
                self.status.setText(f'恢复亮度失败：{exc}')
                return False
            self.last_write = self.initial = None
        return True

    def start_keys(self):
        if self.keys.state() != QProcess.ProcessState.NotRunning:
            return
        self.key_buffer = b''
        self.key_status.setText('等待系统授权…')
        self.keys.start('pkexec', [sys.executable, str(Path(__file__).with_name('key_activity.py'))])

    def key_output(self):
        self.key_buffer += bytes(self.keys.readAllStandardOutput())
        while b'\n' in self.key_buffer:
            line, self.key_buffer = self.key_buffer.split(b'\n', 1)
            if line == b'READY':
                self.key_ready = True
                self.key_status.setText('已连接内置键盘；仅接收按键活动通知')
            elif line == b'KEY':
                self.envelope.press(time.monotonic())
                self.tick()  # Do not wait for the next fade timer tick.

    def key_error(self, error):
        self.key_stopped()

    def key_stopped(self, *_):
        self.key_ready = False
        detail = bytes(self.keys.readAllStandardError()).decode(errors='replace').strip()
        self.key_status.setText('按键检测未运行' + (f'：{detail}' if detail else ''))
        if self.active_mode == 'auto':
            self.pause_control()
            self.restore()

    def set_modes_enabled(self, enabled):
        self.mode_auto.setEnabled(enabled)
        self.mode_always.setEnabled(enabled)

    def pause_control(self):
        self.active_mode = None
        self.controller = None
        self.mode_group.setExclusive(False)
        self.mode_auto.setChecked(False)
        self.mode_always.setChecked(False)
        self.mode_group.setExclusive(True)
        if self.keys.state() != QProcess.ProcessState.NotRunning:
            self.keys.terminate()

    def select_mode(self, mode):
        if not self.mode_auto.isEnabled():
            return
        self.active_mode = mode
        self.mode_auto.setChecked(mode == 'auto')
        self.mode_always.setChecked(mode == 'always')
        self.controller = None
        self.envelope = ActivityEnvelope()
        if mode == 'auto':
            if not self.key_ready:
                self.start_keys()
                self.status.setText('等待按键检测授权；尚未改变灯光。')
        else:
            if self.keys.state() != QProcess.ProcessState.NotRunning:
                self.keys.terminate()
            self.tick()

    def write(self, value):
        if self.initial is None:
            self.initial = self.hardware.read()[1]
        self.hardware.write(value)
        self.last_write = value

    def apply_manual(self):
        self.pause_control()
        value = self.manual.value()
        try:
            if self.hardware is None:
                self.hardware = Hardware()
            self.write(round(value * self.hardware.maximum / 255))
            self.status.setText(f'已应用手动亮度：{value}/255')
        except Exception as exc:
            self.status.setText(str(exc))

    def tick(self):
        try:
            if self.hardware is None:
                self.hardware = Hardware()
            lux, current = self.hardware.read()
            self.plot.lux = lux
            self.plot.update()
            target = value_at(self.data, lux)
            self.readings.setText(f'环境光 {lux:.1f} lux     当前灯光 {current}/{self.hardware.maximum}     曲线目标 {target}/255')
            now = time.monotonic()
            dt, self.last_time = now - self.last_time, now
            if self.active_mode is None or (self.active_mode == 'auto' and not self.key_ready):
                return
            if self.controller is None:
                self.controller = Controller(self.hardware.maximum, current, config=self.data)
            # Keep ambient filtering/hysteresis, but bypass brightness ramp and
            # manual-hold: neither may delay a key flash or defeat idle-off.
            c = self.controller
            alpha = 1 - math.exp(-dt / 3)
            c.filtered = lux if c.filtered is None else c.filtered + alpha * (lux - c.filtered)
            ambient = c.policy.update(c.filtered, now)
            factor = self.envelope.factor(now, self.active_mode == 'always')
            value = round(ambient * self.hardware.maximum / 255 * factor)
            if value != current:
                self.write(value)
            self.status.setText(f'自动调节：{value}/{self.hardware.maximum} · ' +
                               ('常亮' if self.active_mode == 'always' else '按键后 5 秒熄灭'))
        except Exception as exc:
            self.pause_control()
            self.status.setText(f'自动调节已停止：{exc}')

    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.status.setText('系统托盘不可用，关闭窗口将退出程序。')
            return False
        icon = QIcon(str(Path(__file__).with_name('keyboard.svg')))
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip('Kotra-KB-Light · 后台运行')
        menu = QMenu(self)
        menu.addAction('打开设置', self.show_settings)
        menu.addAction('自动调节', lambda: self.select_mode('auto'))
        menu.addAction('常亮', lambda: self.select_mode('always'))
        menu.addSeparator()
        menu.addAction('退出并恢复亮度', self.request_exit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        QApplication.instance().setQuitOnLastWindowClosed(False)
        return True

    def show_settings(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_settings()

    def request_exit(self):
        self.exiting = True
        if self.close():
            QApplication.instance().quit()
        else:
            self.exiting = False

    def closeEvent(self, event):
        if not self.exiting and self.tray is not None and self.tray.isVisible() and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.ignore()
            return
        if not self.discard():
            event.ignore()
            return
        if not self.restore():
            QMessageBox.warning(self, '未能恢复灯光', self.status.text())
        self.timer.stop()
        self.keys.terminate()
        if not self.keys.waitForFinished(1000):
            self.keys.kill()
            self.keys.waitForFinished(1000)
        if self.tray is not None:
            self.tray.hide()
        event.accept()
        if not self.exiting:
            QApplication.instance().quit()


def launch_background(arguments):
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'm1-kbd-auto'
    state.mkdir(parents=True, exist_ok=True)
    log = state / 'gui.log'
    with log.open('a') as output:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--foreground', *arguments],
                         stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                         start_new_session=True, close_fds=True)
    print(f'Kotra-KB-Light 已在后台启动；日志：{log}')
    return 0


def main():
    arguments = sys.argv[1:]
    if '--foreground' not in arguments:
        return launch_background(arguments)
    app = QApplication([sys.argv[0]])
    app.setApplicationName('Kotra-KB-Light')
    app.setApplicationDisplayName('Kotra-KB-Light')
    app.setDesktopFileName('Kotra-KB-Light')
    app.setWindowIcon(QIcon(str(Path(__file__).with_name('keyboard.svg'))))
    lock = QLockFile(str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)) / f'm1-kbd-auto-{os.getuid()}.lock'))
    if not lock.tryLock(100):
        QMessageBox.warning(None, '已经运行', '键盘灯已在运行，请从系统托盘打开设置。')
        return 1
    window = Window()
    tray_available = window.setup_tray()
    if '--hidden' not in arguments or not tray_available:
        window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
