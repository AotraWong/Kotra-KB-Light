#!/usr/bin/env python3
"""Ambient keyboard lighting for Asahi; standard library only."""
import argparse
import logging
import math
from pathlib import Path
import signal
import threading
import time
from curve import load, StepPolicy


def number(path):
    value = float(Path(path).read_text().strip())
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'Invalid nonnegative reading: {path}')
    return value


def sensor_path(root=Path('/sys/bus/iio/devices')):
    candidates = sorted(root.glob('iio:device*/in_illuminance_input'))
    apple = [p for p in candidates if (p.parent / 'name').read_text().strip() == 'aop-sensors-als']
    candidates = apple or candidates
    if len(candidates) != 1:
        raise ValueError('Need exactly one ALS sensor; use --sensor PATH. '
                         'The kernel must expose calibrated in_illuminance_input (lux).')
    return candidates[0]


class Controller:
    def __init__(self, maximum, initial, hold=60, config=None):
        self.maximum = maximum
        self.expected = initial
        self.hold = hold
        self.until = 0
        self.filtered = None
        self.policy = StepPolicy(config or load())
        self.target = initial

    def update(self, lux, current, now, dt):
        if not math.isfinite(lux) or lux < 0:
            raise ValueError('Invalid lux')
        if current != self.expected:
            self.until = now + self.hold
            self.expected = current
        # Time-based smoothing; reset naturally after a long sleep.
        alpha = 1 - math.exp(-dt / 3)
        self.filtered = lux if self.filtered is None else self.filtered + alpha * (lux - self.filtered)
        desired = round(self.maximum * self.policy.update(self.filtered, now) / 255)
        self.target = desired
        if now < self.until:
            return current
        step = max(1, round(self.maximum * .10 * min(dt, 2)))
        return current + max(-step, min(step, self.target - current))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='JSON curve configuration')
    parser.add_argument('--sensor', type=Path, help='Processed illuminance input, in lux (not raw)')
    parser.add_argument('--led', type=Path, default=Path('/sys/class/leds/kbd_backlight'))
    parser.add_argument('--dry-run', action='store_true', help='Read hardware and simulate changes only')
    parser.add_argument('--samples', type=int, default=0, help='Stop after N samples; 0 runs continuously')
    parser.add_argument('--manual-hold', type=float, default=60, help='Seconds to respect external brightness changes')
    args = parser.parse_args()
    if args.samples < 0 or not math.isfinite(args.manual_hold) or args.manual_hold < 0:
        parser.error('samples and manual-hold must be nonnegative and finite')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        sensor = args.sensor or sensor_path()
        maximum = int(number(args.led / 'max_brightness'))
        if maximum <= 0:
            raise ValueError('Invalid max_brightness')
        brightness = args.led / 'brightness'
        initial = int(number(brightness))
        if initial > maximum:
            raise ValueError('Brightness exceeds maximum')
        control = Controller(maximum, initial, args.manual_hold, load(args.config) if args.config else load())
        simulated = initial
        last_write = None
        logging.info('sensor=%s led=%s max=%s dry_run=%s', sensor, args.led, maximum, args.dry_run)
        previous = time.monotonic() - 1
        count = 0
        errors = 0
        try:
            while not stop.is_set():
                now = time.monotonic()
                dt = now - previous
                previous = now
                try:
                    lux = number(sensor)
                    current = simulated if args.dry_run else int(number(brightness))
                    if not 0 <= current <= maximum:
                        raise ValueError('Brightness out of range')
                    next_value = control.update(lux, current, now, dt)
                    if args.dry_run:
                        simulated = next_value
                        logging.info('lux=%.2f filtered=%.2f simulated=%d/%d', lux, control.filtered, next_value, maximum)
                    elif next_value != current:
                        brightness.write_text(f'{next_value}\n')
                        last_write = next_value
                        logging.info('lux=%.2f brightness=%d/%d', lux, next_value, maximum)
                    control.expected = next_value
                    errors = 0
                except (OSError, ValueError) as exc:
                    errors += 1
                    logging.warning('No adjustment: %s', exc)
                    if errors >= 5:
                        raise RuntimeError('Five consecutive read/write failures; stopping') from exc
                count += 1
                if args.samples and count >= args.samples:
                    break
                stop.wait(1)
        finally:
            # Do not undo a later manual adjustment by another controller.
            if not args.dry_run and last_write is not None:
                try:
                    if int(number(brightness)) == last_write:
                        brightness.write_text(f'{initial}\n')
                except (OSError, ValueError) as exc:
                    logging.warning('Could not restore initial brightness: %s', exc)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        logging.error('%s', exc)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
