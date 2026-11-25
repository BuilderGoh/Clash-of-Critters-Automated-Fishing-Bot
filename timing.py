"""Configurable timing lead for ADB; no input or screen capture here."""
from dataclasses import dataclass

@dataclass
class TimingLead:
    previous: tuple | None = None
    velocity: float | None = None
    last_zone: tuple | None = None
    resolved_details: tuple | None = None
    frame_dt: float = 0.0

    def note_click(self):
        # Do not reuse an invisible target after sending a reel tap.
        self.last_zone = None

    def reset(self):
        self.previous = None
        self.velocity = None
        self.last_zone = None
        self.resolved_details = None
        self.frame_dt = 0.0

    def step(self, state, hit, details, stamp, lead_ms):
        if state != 'timing' or details is None:
            self.reset()
            return hit, None
        x, left, right, _ = details
        self.resolved_details = details
        if left is None or right is None:
            if self.last_zone is None:
                self.reset(); return False, None
            l,r,seen = self.last_zone
            # Reuse a recently seen zone ONLY if the red marker can cover it.
            if stamp-seen>0.12 or stamp<seen or not (l-18<=x<=r+18):
                self.reset(); return False, None
            left,right=l,r
            hit=left-.5<=x<=right+.5
            self.resolved_details=(x,left,right,round(max(left-x,x-right,0),1))
        else:
            # A float can hide only one side of a target. Preserve a recently
            # measured endpoint when the surviving edge is stationary and the
            # disappearing edge is beside the marker. Never extend a new zone.
            old=self.last_zone
            if old is not None and 0<=stamp-old[2]<=.12:
                l,r,_=old
                if abs(right-r)<=3 and left>l+2 and abs(left-x)<=26 and l-26<=x<=right:
                    left=l
                elif abs(left-l)<=3 and right<r-2 and abs(right-x)<=26 and left<=x<=r+26:
                    right=r
                else: self.last_zone=(left,right,stamp)
            else: self.last_zone=(left,right,stamp)
            self.resolved_details=(x,left,right,round(max(left-x,x-right,0),1))
            hit=left-.5<=x<=right+.5
        if self.previous is not None:
            old_x, old_t, old_left, old_right = self.previous
            dt = stamp - old_t
            overlap = max(0, min(right, old_right) - max(left, old_left)+1)
            same_zone = overlap >= .55 * min(right-left+1, old_right-old_left+1)
            v = (x-old_x)/dt if dt>0 else 0
            if .008 <= dt <= .45 and same_zone and 35 <= abs(v) <= 850:
                self.velocity = v if self.velocity is None or v*self.velocity<=0 else .65*v+.35*self.velocity
                self.frame_dt = dt
            elif same_zone and (0<=dt<.008 or (abs(x-old_x)<.5 and dt<=.08)):
                # Short decoder bursts or repeated game frames are not zero
                # velocity measurements. Keep the last moving sample briefly.
                pass
            else:
                self.velocity = None
                self.frame_dt = 0.0
        if self.previous is None or (stamp-self.previous[1]>=.008 and (abs(x-self.previous[0])>=.5 or stamp-self.previous[1]>.08 or self.velocity is None)):
            self.previous = (x, stamp, left, right)
        if lead_ms <= 0 or self.velocity is None:
            return hit, None
        predicted = x + self.velocity * lead_ms/1000
        if not 205 <= predicted <= 550:
            return False, (round(predicted,1), round(self.velocity,1))
        width=right-left+1
        inset = min(5, max(0,(width-3)*.10))
        # A narrow zone may cross between frame samples. Permit a small
        # nearest-frame tolerance only when the marker is approaching it.
        approaching=(left-predicted)*self.velocity>0 if predicted<left else (right-predicted)*self.velocity>0 if predicted>right else False
        slack=min(3.0,abs(self.velocity)*self.frame_dt/2) if width<=12 and approaching else 0.0
        return left-.5+inset-slack <= predicted <= right+.5-inset+slack, (round(predicted,1), round(self.velocity,1))
