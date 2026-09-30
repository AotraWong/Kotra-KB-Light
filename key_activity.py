#!/usr/bin/env python3
"""Emit activity only from the built-in keyboard; never output key identities."""
import os
from pathlib import Path
import pwd
import select
import struct
import sys
import time

EVENT = struct.Struct('@llHHi')


def keyboard_path(root=Path('/sys/class/input')):
    matches = [p for p in root.glob('event*')
               if (p / 'device/name').read_text().strip() == 'Apple SPI Keyboard']
    if len(matches) != 1:
        raise RuntimeError('未找到唯一的 Apple SPI Keyboard')
    return Path('/dev/input') / matches[0].name


def main():
    fd = os.open(keyboard_path(), os.O_RDONLY | os.O_NONBLOCK)
    # Retain only the already-open keyboard descriptor, not root privileges.
    if os.geteuid() == 0:
        uid = int(os.environ.get('PKEXEC_UID', '65534'))
        if uid == 0:
            uid = 65534
        user = pwd.getpwuid(uid)
        os.setgroups([])
        os.setgid(user.pw_gid)
        os.setuid(uid)
    print('READY', flush=True)
    buffered = b''
    last_emit = 0
    try:
        while True:
            select.select([fd], [], [])
            chunk = os.read(fd, EVENT.size * 64)
            if not chunk:
                raise RuntimeError('键盘已断开')
            buffered += chunk
            activity = False
            while len(buffered) >= EVENT.size:
                _, _, event_type, _, value = EVENT.unpack(buffered[:EVENT.size])
                buffered = buffered[EVENT.size:]
                activity |= event_type == 1 and value in (1, 2)
            now = time.monotonic()
            if activity and now - last_emit >= .02:
                print('KEY', flush=True)
                last_emit = now
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
