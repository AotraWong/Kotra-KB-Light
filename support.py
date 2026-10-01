"""Bilingual About page."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox
import i18n

URL = 'https://github.com/AotraWong/Kotra-KB-Light'


class SupportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(560, 300)
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
        self.browser.setHtml(
            f'<h1>Kotra-KB-Light</h1><p>{description}</p>'
            f'<p>{author}: <b>AotraWong</b></p>'
            f'<p>GitHub: <a href="{URL}">{URL}</a></p>')
        self.buttons.button(QDialogButtonBox.StandardButton.Close).setText(i18n.tr('关闭'))
