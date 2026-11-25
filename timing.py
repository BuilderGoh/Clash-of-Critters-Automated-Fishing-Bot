"""Configurable timing lead for ADB; no input or screen capture here."""
from dataclasses import dataclass

@dataclass
class TimingLead:
    previous: tuple | None = None
    velocity: float | None = None

    def reset(self):
        self.previous = None
        self.velocity = None

    def step(self, state, hit, details, stamp, lead_ms):
        if state != 'timing' or details is None:
            self.reset()
            return hit, None
        x, left, right, _ = details
        if self.previous is not None:
            old_x, old_t, old_left, old_right = self.previous
            dt = stamp - old_t
            overlap = max(0, min(right, old_right) - max(left, old_left))
            same_zone = overlap >= .55 * min(right-left, old_right-old_left)
            v = (x-old_x)/dt if dt>0 else 0
            if .012 <= dt <= .45 and same_zone and 35 <= abs(v) <= 850:
                # Do not smooth across a direction reversal.
                self.velocity = v if self.velocity is None or v*self.velocity<=0 else .65*v+.35*self.velocity
            else:
                self.velocity = None
        self.previous = (x, stamp, left, right)
        if lead_ms <= 0 or self.velocity is None:
            return hit, None
        predicted = x + self.velocity * lead_ms/1000
        # Extrapolation past the track endpoints is not reliable near a bounce.
        if not 205 <= predicted <= 550:
            return False, (round(predicted,1), round(self.velocity,1))
        # Prefer the interior of the target rather than the trailing edge.
        inset = min(5, (right-left)*.10)
        return left+inset <= predicted <= right-inset, (round(predicted,1), round(self.velocity,1))
