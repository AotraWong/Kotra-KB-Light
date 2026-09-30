"""Validated, shared step-curve configuration and debounce policy."""
from bisect import bisect_right
import json
import math
from pathlib import Path

PRESET = Path(__file__).parent / 'presets' / 'inverted-u.json'


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('配置必须是 JSON 对象')
    if data.get('version') != 1:
        raise ValueError('配置版本必须为 1')
    bands = data.get('bands')
    if not isinstance(bands, list) or not 2 <= len(bands) <= 100:
        raise ValueError('需要 2–100 个档位')
    previous = -1
    for band in bands:
        if not isinstance(band, dict):
            raise ValueError('档位必须是对象')
        lux, brightness = band['lux'], band['brightness']
        if isinstance(lux, bool) or not isinstance(lux, (float, int)) or not math.isfinite(lux) or not 0 <= lux <= 1000000 or lux <= previous:
            raise ValueError('lux 必须严格递增，范围 0–1000000')
        if isinstance(brightness, bool) or not isinstance(brightness, int) or not 0 <= brightness <= 255:
            raise ValueError('亮度必须是 0–255 的整数')
        previous = lux
    if bands[0]['lux'] != 0:
        raise ValueError('第一个档位必须从 0 lux 开始')
    for key, low, high in [('hysteresis', 0, .5), ('settle_seconds', 0, 60)]:
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key} 范围必须为 {low}–{high}')
    return data


def load(path=PRESET):
    return validate(json.loads(Path(path).read_text()))


def save(path, data):
    validate(data)
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def band_index(data, lux):
    if not math.isfinite(lux) or lux < 0:
        raise ValueError('无效的环境光读数')
    return bisect_right([b['lux'] for b in data['bands']], lux) - 1


def value_at(data, lux):
    return data['bands'][band_index(data, lux)]['brightness']


class StepPolicy:
    def __init__(self, data):
        self.data = validate(data)
        self.index = None
        self.pending = None
        self.since = 0

    def update(self, lux, now):
        candidate = band_index(self.data, lux)
        if self.index is None:
            self.index = candidate
        bands = self.data['bands']
        h = self.data['hysteresis']
        if candidate > self.index and lux < bands[candidate]['lux'] * (1 + h):
            candidate -= 1
        elif candidate < self.index and lux > bands[candidate + 1]['lux'] * (1 - h):
            candidate += 1
        if candidate == self.index:
            self.pending = None
        else:
            if self.pending != candidate:
                self.pending, self.since = candidate, now
            if now - self.since >= self.data['settle_seconds']:
                self.index, self.pending = candidate, None
        return bands[self.index]['brightness']
