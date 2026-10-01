import unittest
from unittest.mock import patch, Mock
from PySide6.QtWidgets import QSystemTrayIcon
import test_gui
import gui


class TrayTests(unittest.TestCase):
    setUpClass = classmethod(test_gui.GuiTests.setUpClass.__func__)
    setUp = test_gui.GuiTests.setUp
    def tearDown(self):
        self.w.dirty = False
        self.w.exiting = True
        self.w.close()
        self.app.setQuitOnLastWindowClosed(True)

    def test_close_hides_without_stopping_control(self):
        with patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=True):
            self.w.setup_tray()
            self.w.show()
            self.w.timer.start()
            self.w.close()
            self.assertFalse(self.w.isVisible())
            self.assertTrue(self.w.timer.isActive())
            self.assertTrue(self.w.tray.isVisible())
            self.w.show_settings()
            self.assertTrue(self.w.isVisible())

    def test_exit_restores_and_stops(self):
        self.w.manual.setValue(100)
        self.w.apply_manual()
        self.w.request_exit()
        self.assertEqual(self.hw.current, 20)
        self.assertFalse(self.w.timer.isActive())

    def test_no_tray_close_exits(self):
        with patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=False):
            self.assertFalse(self.w.setup_tray())
            self.w.show()
            self.w.close()
            self.assertFalse(self.w.timer.isActive())

    def test_background_launch_detaches(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp, patch.dict(gui.os.environ, {'XDG_STATE_HOME': tmp}), patch('gui.subprocess.Popen') as popen:
            self.assertEqual(gui.launch_background(['--hidden']), 0)
            from pathlib import Path
            self.assertTrue((Path(tmp) / 'Kotra-KB-Light' / 'gui.log').is_file())
            self.assertFalse((Path(tmp) / 'm1-kbd-auto').exists())
            args, kwargs = popen.call_args
            self.assertIn('--foreground', args[0])
            self.assertIn('--hidden', args[0])
            self.assertTrue(kwargs['start_new_session'])
            self.assertEqual(kwargs['stdin'], gui.subprocess.DEVNULL)
