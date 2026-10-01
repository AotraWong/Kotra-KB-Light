"""Small live Chinese/English UI catalogue; source text remains Chinese."""
from PySide6 import QtWidgets

language = 'zh'
TRANSLATIONS = {
'曲线配置': 'Curve configuration',
'     曲线目标 ': '     Curve target ', ' lux     当前灯光 ': ' lux     Current ',
' 秒': ' s', '关于': 'About', '关闭': 'Close',
'Kotra-KB-Light · 后台运行': 'Kotra-KB-Light · Running in background',
'UPower 调光失败：': 'UPower brightness request failed: ',
'亮度超出范围': 'Brightness out of range', '保存失败': 'Save failed', '保存曲线': 'Save curve',
'保存配置…': 'Save configuration…',
'保留 0 lux 起始档位，且至少需要两个档位。': 'Keep the first band at 0 lux and at least two bands.',
'修改已用于预览；尚未保存。可重新开启自动调节。': 'Changes shown in the chart, not saved. Select a mode to resume control.',
'倒 U 预设': 'Inverted-U preset', '切换幅度': 'Switching margin', '删除所选档位': 'Remove selected band',
'尚未接管灯光；请选择自动调节或常亮。': 'Not controlling the light. Select Automatic or Always on.',
'已应用手动亮度：': 'Manual brightness applied: ', '已经运行': 'Already running',
'已载入倒 U 预设': 'Inverted-U preset loaded',
'已连接内置键盘；仅接收按键活动通知': 'Built-in keyboard connected; receiving activity notifications only',
'常亮': 'Always on', '应用手动亮度': 'Apply manual brightness', '恢复亮度失败：': 'Restore failed: ',
'手动亮度': 'Manual brightness',
'手动应用会停止自动调节；关闭窗口会尝试恢复接管前亮度。': 'Manual application stops automatic control; exiting restores the previous brightness.',
'打开失败': 'Open failed', '打开曲线': 'Open curve', '打开设置': 'Open settings', '打开配置…': 'Open configuration…',
'持续时间': 'Duration', '按键后 5 秒熄灭': 'Off 5 seconds after the last key',
'按键检测未运行': 'Keyboard detection is not running',
'按键模式：需要授权；不读取到界面的具体键值': 'Automatic mode requires authorization; no key identities are sent to the UI',
'按键立即亮起 → 保持 1 秒 → 渐暗 4 秒 → 熄灭；再次按键重新计时。': 'Key press → light on immediately → hold 1 s → fade 4 s → off. Each press restarts the timer.',
'换档配置': 'Band switching', '放弃未保存的曲线修改？': 'Discard unsaved curve changes?',
'无效的最大亮度': 'Invalid maximum brightness', '无法保存': 'Cannot save',
'无法连接 UPower 键盘灯接口，请在本机桌面会话运行': 'Cannot connect to UPower keyboard backlight. Run in the local desktop session.',
'曲线查询': 'Curve lookup', '未保存的修改': 'Unsaved changes', '未能恢复灯光': 'Could not restore brightness',
'正在读取环境光…': 'Reading ambient light…', '添加档位': 'Add band', '环境光 ': 'Ambient light ',
'环境光 lux（对数刻度；阶梯配置）': 'Ambient lux (log scale; step curve)',
'环境光需超出档位边界的比例，用于避免反复切换。': 'Margin beyond each band boundary to prevent repeated switching.',
'等待按键检测授权；尚未改变灯光。': 'Waiting for keyboard authorization; brightness unchanged.',
'等待系统授权…': 'Waiting for system authorization…',
'系统托盘不可用，关闭窗口将退出程序。': 'System tray unavailable. Closing the window will exit.',
'自动调节': 'Automatic', '自动调节已停止：': 'Automatic control stopped: ', '自动调节：': 'Automatic control: ',
'自定义曲线': 'Custom curve', '请先修正无效档位。': 'Correct invalid bands first.',
'请另存为自定义配置，保留内置预设。': 'Save as a custom configuration to preserve the built-in preset.',
'起始环境光（lux）': 'Starting light (lux)', '载入倒 U 预设': 'Load inverted-U preset',
'运行控制': 'Controls', '退出并恢复亮度': 'Quit and restore brightness', '配置已保存': 'Configuration saved',
'配置无效：': 'Invalid configuration: ', '键盘亮度 / 255': 'Keyboard brightness / 255',
'键盘亮度（0–255）': 'Brightness (0–255)',
'键盘灯已在运行，请从系统托盘打开设置。': 'Kotra-KB-Light is running. Open settings from the system tray.',
'），未计入换档配置和延迟': '), before switching margins and delay',
'；曲线图保留上一个有效配置。': '; chart retains the last valid configuration.',
'配置版本必须为 1': 'Configuration version must be 1', '配置必须是 JSON 对象': 'Configuration must be a JSON object',
'需要 2–100 个档位': 'Use 2–100 bands', '档位必须是对象': 'Each band must be an object',
'lux 必须严格递增，范围 0–1000000': 'Lux must increase strictly within 0–1000000',
'亮度必须是 0–255 的整数': 'Brightness must be an integer from 0 to 255',
'第一个档位必须从 0 lux 开始': 'The first band must start at 0 lux',
' 范围必须为 ': ' must be within ', '无效的环境光读数': 'Invalid ambient light reading',
'未找到唯一的 Apple SPI Keyboard': 'Could not find exactly one Apple SPI Keyboard',
'键盘已断开': 'Keyboard disconnected',
}


def tr(text):
    if language == 'zh':
        return text
    for source in sorted(TRANSLATIONS, key=len, reverse=True):
        text = text.replace(source, TRANSLATIONS[source])
    return text


class TextMixin:
    def setText(self, text):
        self.source_text = text
        super().setText(tr(text))

    def retranslate(self):
        super().setText(tr(self.source_text))


class QLabel(TextMixin, QtWidgets.QLabel):
    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self.setText(text)


class QPushButton(TextMixin, QtWidgets.QPushButton):
    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self.setText(text)


class QGroupBox(QtWidgets.QGroupBox):
    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self.source_text = text
        self.retranslate()

    def retranslate(self):
        self.setTitle(tr(self.source_text))
