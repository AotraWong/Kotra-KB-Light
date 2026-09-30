import unittest
from unittest.mock import patch
from activity import ActivityEnvelope
import test_gui


class EnvelopeTests(unittest.TestCase):
    def test_timing_and_retrigger(self):
        e = ActivityEnvelope()
        self.assertEqual(e.factor(100), 0)
        e.press(100)
        for elapsed, expected in [(0,1),(.5,1),(1,1),(2,.75),(3,.5),(4,.25),(5,0),(10,0)]:
            self.assertAlmostEqual(e.factor(100 + elapsed), expected)
        e.press(103)
        self.assertEqual(e.factor(103), 1)
        self.assertEqual(e.factor(108), 0)
        self.assertEqual(e.factor(1000, always_on=True), 1)


class ActivityGuiTests(unittest.TestCase):
    setUpClass = classmethod(test_gui.GuiTests.setUpClass.__func__)
    setUp = test_gui.GuiTests.setUp
    tearDown = test_gui.GuiTests.tearDown

    def test_actual_output_envelope(self):
        w = self.w
        w.key_ready = True
        w.select_mode('auto')
        with patch('gui.time.monotonic', return_value=100):
            w.last_time = 99
            w.envelope.press(100)
            w.tick()
        self.assertEqual(self.hw.current, 64)
        with patch('gui.time.monotonic', return_value=103):
            w.tick()
        self.assertEqual(self.hw.current, 32)
        with patch('gui.time.monotonic', return_value=105):
            w.tick()
        self.assertEqual(self.hw.current, 0)
        w.select_mode('always')
        w.tick()
        self.assertEqual(self.hw.current, 64)

    def test_bright_environment_stays_off_on_key(self):
        self.hw.read = lambda: (1000, self.hw.current)
        self.w.key_ready = True
        self.w.select_mode('auto')
        self.w.envelope.press(__import__('time').monotonic())
        self.w.tick()
        self.assertEqual(self.hw.current, 0)
        self.w.select_mode('always')
        self.w.tick()
        self.assertEqual(self.hw.current, 0)
