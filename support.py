"""Bilingual About page."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox
import i18n

URL = 'https://github.com/AotraWong/Kotra-KB-Light'


class SupportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(620, 470)
        layout = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        layout.addWidget(self.browser)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.hide)
        layout.addWidget(self.buttons)
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(i18n.tr('关于') + ' · Kotra-KB-Light')
        author = '作者' if i18n.language == 'zh' else 'Author'
        description = ('适用于 Asahi Linux / KDE 的键盘背光调节工具。'
                       if i18n.language == 'zh' else
                       'Keyboard backlight control for Asahi Linux and KDE.')
        if i18n.language == 'zh':
            dependencies = (
                '<h2>使用的包与组件</h2><ul>'
                '<li><b>PySide6 ≥ 6.6, &lt; 7</b>：Qt 6 的 Python 绑定；使用 QtCore、QtGui、QtWidgets 和 QtDBus。</li>'
                '<li><b>Python 3 标准库</b>：文件与 JSON 配置、进程管理、计时和 Linux 输入事件读取。</li>'
                '<li><b>UPower / D-Bus</b>：系统键盘背光控制。</li>'
                '<li><b>polkit（pkexec）</b>：按键检测助手的权限授权。</li>'
                '</ul><p>UPower、D-Bus 和 polkit 是系统组件，不是 pip 包。第三方组件遵循各自的许可证。</p>')
            license_label = '许可证'
        else:
            dependencies = (
                '<h2>Packages and components</h2><ul>'
                '<li><b>PySide6 ≥ 6.6, &lt; 7</b>: Python bindings for Qt 6; uses QtCore, QtGui, QtWidgets and QtDBus.</li>'
                '<li><b>Python 3 standard library</b>: files and JSON configuration, process management, timing and Linux input events.</li>'
                '<li><b>UPower / D-Bus</b>: system keyboard backlight control.</li>'
                '<li><b>polkit (pkexec)</b>: authorization for the keyboard activity helper.</li>'
                '</ul><p>UPower, D-Bus and polkit are system components, not pip packages. Third-party components retain their own licenses.</p>')
            license_label = 'License'
        self.browser.setHtml(
            f'<h1>Kotra-KB-Light</h1><p>{description}</p>'
            f'<p>{author}: <b>AotraWong</b></p>'
            f'<p>GitHub: <a href="{URL}">{URL}</a></p>'
            f'<p>{license_label}: <a href="{URL}/blob/HEAD/LICENSE">GNU GPL v3</a>'
            ' (GNU General Public License, version 3)</p>' + dependencies)
        self.buttons.button(QDialogButtonBox.StandardButton.Close).setText(i18n.tr('关闭'))
