import unittest
from unittest.mock import patch
import i18n
import test_gui
from PySide6.QtWidgets import QSystemTrayIcon


class LanguageTests(unittest.TestCase):
    setUpClass = classmethod(test_gui.GuiTests.setUpClass.__func__)
    def setUp(self):
        i18n.language = 'zh'
        test_gui.GuiTests.setUp(self)
    def tearDown(self):
        if self.w.support_dialog:
            self.w.support_dialog.close()
        self.w.exiting = True
        test_gui.GuiTests.tearDown(self)
        self.app.setQuitOnLastWindowClosed(True)
        i18n.language = 'zh'
    def test_live_switch_preserves_control_and_edits(self):
        self.w.hysteresis.setValue(15)
        self.w.select_mode('always')
        controller = self.w.controller
        writes = list(self.hw.writes)
        self.w.toggle_language()
        self.assertEqual(self.w.mode_auto.text(), 'Automatic')
        self.assertEqual(self.w.shift_button.text(), 'Band switching')
        self.assertEqual(self.w.active_mode, 'always')
        self.assertIs(self.w.controller, controller)
        self.assertEqual(self.hw.writes, writes)
        self.assertTrue(self.w.dirty)
        self.assertEqual(self.w.data['hysteresis'], .15)
        self.w.tick()
        self.assertIn('Ambient light', self.w.readings.text())
        self.w.toggle_language()
        self.assertEqual(self.w.mode_auto.text(), '自动调节')
    def test_support_and_tray_switch(self):
        with patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=True):
            self.w.setup_tray()
        self.w.show_support()
        self.w.toggle_language()
        self.assertIn('About', self.w.support_dialog.windowTitle())
        self.assertIn('AotraWong', self.w.support_dialog.browser.toPlainText())
        self.assertIn('https://github.com/AotraWong/Kotra-KB-Light', self.w.support_dialog.browser.toPlainText())
        self.assertIn('About', [a.text() for a in self.w.tray.contextMenu().actions()])
        self.assertEqual(self.hw.writes, [])
