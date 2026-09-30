"""One second hold, four second linear fade, retriggerable on every key."""
class ActivityEnvelope:
    def __init__(self):
        self.last_key = None

    def press(self, now):
        self.last_key = now

    def factor(self, now, always_on=False):
        if always_on:
            return 1.0
        if self.last_key is None:
            return 0.0
        elapsed = max(0, now - self.last_key)
        return 1.0 if elapsed <= 1 else max(0.0, (5 - elapsed) / 4)
