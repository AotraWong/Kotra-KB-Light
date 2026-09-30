import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from kbd_auto import Controller, number, sensor_path
from curve import load, StepPolicy, value_at, validate, save


class Tests(unittest.TestCase):
    def test_dark_and_bright_converge(self):
        c = Controller(255, 0)
        current = 0
        for n in range(40):
            current = c.update(0, current, n, 1)
            c.expected = current
        self.assertEqual(current, 13)
        for n in range(40, 100):
            current = c.update(300, current, n, 1)
            c.expected = current
        self.assertEqual(current, 0)

    def test_hysteresis(self):
        policy = StepPolicy(load())
        self.assertEqual(policy.update(40, 0), 89)
        self.assertEqual(policy.update(82, 5), 89)
        self.assertEqual(policy.update(90, 6), 89)
        self.assertEqual(policy.update(90, 8), 64)
        self.assertEqual(policy.update(75, 9), 64)
        self.assertEqual(policy.update(70, 10), 64)
        self.assertEqual(policy.update(70, 12), 89)

    def test_curve_boundaries_and_roundtrip(self):
        data = load()
        for lux, expected in [(0,13),(1.99,13),(2,26),(10,51),(30,89),(80,64),(150,26),(250,0),(99999,0)]:
            self.assertEqual(value_at(data,lux), expected)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'curve.json'
            save(path,data)
            self.assertEqual(load(path),data)
        data['bands'][1]['lux'] = 0
        with self.assertRaises(ValueError):
            validate(data)

    def test_manual_override(self):
        c = Controller(255, 0)
        self.assertEqual(c.update(0, 120, 10, 1), 120)
        self.assertEqual(c.update(0, 120, 69, 1), 120)
        self.assertLess(c.update(0, 120, 71, 1), 120)

    def test_invalid(self):
        c = Controller(255, 0)
        for value in [-1, math.nan, math.inf]:
            with self.assertRaises(ValueError):
                c.update(value, 0, 0, 1)

    def test_discovery_and_io(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            device = root / 'iio:device3'
            device.mkdir()
            (device / 'name').write_text('aop-sensors-als\n')
            sensor = device / 'in_illuminance_input'
            sensor.write_text('42.5\n')
            self.assertEqual(sensor_path(root), sensor)
            self.assertEqual(number(sensor), 42.5)
            (root / 'brightness').write_text('10\n')
            (root / 'max_brightness').write_text('255\n')
            base = [sys.executable, str(Path(__file__).with_name('kbd_auto.py')),
                    '--sensor', str(sensor), '--led', str(root), '--samples', '1']
            result = subprocess.run(base + ['--dry-run'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'brightness').read_text(), '10\n')
            result = subprocess.run(base, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('brightness=', result.stderr)
            self.assertEqual((root / 'brightness').read_text(), '10\n')


if __name__ == '__main__':
    unittest.main()
