import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtWidgets import QApplication, QTableWidgetItem
from gui import Window


class FakeHardware:
    maximum = 255
    def __init__(self):
        self.current = 20
        self.writes = []
        self.fail = False
    def read(self):
        return 120, self.current
    def write(self, value):
        if self.fail:
            raise RuntimeError('permission denied')
        self.current = value
        self.writes.append(value)


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
    def setUp(self):
        self.hw = FakeHardware()
        self.w = Window(self.hw)
        self.w.timer.stop()
    def tearDown(self):
        self.w.dirty = False
        self.w.close()
    def test_idle_manual_and_restore(self):
        self.w.tick()
        self.assertEqual(self.hw.writes, [])
        self.w.manual.setValue(128)
        self.w.apply_manual()
        self.assertIsNone(self.w.active_mode)
        self.assertEqual(self.hw.current, 128)
        self.assertTrue(self.w.restore())
        self.assertEqual(self.hw.current, 20)
    def test_mode_auto_requests_detection_without_writing(self):
        from unittest.mock import patch
        with patch.object(self.w, 'start_keys') as start:
            self.w.select_mode('auto')
            start.assert_called_once()
            self.w.tick()
            self.assertEqual(self.hw.writes, [])
            self.assertTrue(self.w.mode_auto.isChecked())
        self.w.select_mode('always')
        self.assertFalse(self.w.mode_auto.isChecked())
        self.assertTrue(self.w.mode_always.isChecked())
        self.assertEqual(self.hw.current, 64)

    def test_invalid_editor_stops_auto(self):
        self.w.select_mode('always')
        self.w.table.setItem(1, 0, QTableWidgetItem('0'))
        self.assertFalse(self.w.mode_auto.isEnabled())
        self.assertIsNone(self.w.active_mode)
        self.w.table.setItem(1, 0, QTableWidgetItem('3'))
        self.assertTrue(self.w.mode_auto.isEnabled())
        self.assertEqual(self.w.data['bands'][1]['lux'], 3)
    def test_permission_failure_visible(self):
        self.hw.fail = True
        self.w.apply_manual()
        self.assertIn('permission denied', self.w.status.text())
        self.assertEqual(self.hw.writes, [])
    def test_external_change_not_restored(self):
        self.w.apply_manual()
        self.hw.current = 200
        self.w.restore()
        self.assertEqual(self.hw.current, 200)
