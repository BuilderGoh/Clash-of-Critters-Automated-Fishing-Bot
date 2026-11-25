"""Visual detector calibrated on a 720 x 1280 recording; coordinates are game-relative."""
import cv2
import numpy as np
from dataclasses import dataclass
from pathlib import Path
W,H=720,1280
HEADER=cv2.imread(str(Path(__file__).with_name('header.png')),0)

REWARD_TITLE=cv2.imread(str(Path(__file__).with_name("reward_title.png")),0)

RECORD_TITLE=cv2.imread(str(Path(__file__).with_name("record_title.png")),0)

def locate(frame):
    h,w=frame.shape[:2]; gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    # Search for the contest heading, not emulator chrome. Restrict scale to plausible portrait viewports.
    upper=min(h/1280,w/720); best=None
    for s in np.linspace(upper*.65,upper,42):
        tw,th=round(350*s),round(88*s)
        if tw<20 or th<5:continue
        template=cv2.resize(HEADER,(tw,th),interpolation=cv2.INTER_AREA)
        m=cv2.matchTemplate(gray[:max(th,round(h*.35))],template,cv2.TM_CCOEFF_NORMED)
        _,score,_,(x,y)=cv2.minMaxLoc(m)
        left=round(x-185*s); top=round(y-12*s); right=left+round(720*s); bottom=top+round(1280*s)
        if left < -5 or top < -5 or right>w+5 or bottom>h+5:continue
        if best is None or score>best[0]:best=(score,(max(0,left),max(0,top),min(w,right),min(h,bottom)))
    if best is None or best[0]<.67:raise ValueError('Fishing Contest heading not found; open the main fishing screen.')
    return best[1]

def norm(frame,rect):
    l,t,r,b=rect
    return cv2.resize(frame[t:b,l:r],(W,H),interpolation=cv2.INTER_AREA)

def fraction(a,lo,hi):return cv2.inRange(a,lo,hi).mean()/255

def observe(frame):
    hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
    # Rewards overlay is dark, with distinct yellow heading and a green claim button.
    header=hsv[180:310,170:550]; claim=hsv[1088:1163,225:495]
    reward=(fraction(header,(15,110,160),(38,255,255))>.10 and np.median(hsv[320:450,:,2])<100)
    if reward:return ('claim' if fraction(claim,(30,100,120),(70,255,255))>.30 else 'reward_wait',False,None)
    # The alternate reward card has a green/yellow title above a bright gold or purple panel.
    title=cv2.cvtColor(frame[155:300,125:595],cv2.COLOR_BGR2GRAY)
    score=cv2.minMaxLoc(cv2.matchTemplate(title,REWARD_TITLE,cv2.TM_CCOEFF_NORMED))[1]
    record_score=cv2.minMaxLoc(cv2.matchTemplate(title,RECORD_TITLE,cv2.TM_CCOEFF_NORMED))[1]
    # A bright saturated card between dimmed upper and lower game regions.
    panel=fraction(hsv[390:880],(0,80,120),(179,255,255))
    upper=np.median(hsv[20:145,:,2]); lower=np.median(hsv[1160:1220,:,2])
    if max(score,record_score)>.68 and panel>.22 and upper<150 and lower<130:
        return 'dismiss',False,None
    button=hsv[960:1145,265:455]
    green=fraction(button,(35,110,120),(85,255,255)); purple=fraction(button,(125,90,130),(169,255,255))
    if green>.23:return 'cast',False,None
    if purple>.23:
        prompt=fraction(hsv[765:825,180:540],(125,85,100),(169,255,255))
        if prompt>.28:return 'bite',False,None
        yellow=cv2.inRange(hsv[850:872,205:550],(20,145,175),(38,255,255))
        area=hsv[830:870,195:560]; red=cv2.inRange(area,(0,125,130),(12,255,255))|cv2.inRange(area,(170,125,130),(179,255,255))
        n,_,stats,cent=cv2.connectedComponentsWithStats(red)
        markers=[(int(s[4]),float(c[0]+195)) for s,c in zip(stats[1:],cent[1:]) if 10<=s[2]<=48 and 10<=s[3]<=40 and s[4]>100]
        yy=np.flatnonzero((yellow>0).sum(axis=0)>=8)+205
        if markers and len(yy)>=4:
            mx=max(markers)[1]; gap=float(np.min(np.abs(yy-mx))); hit=gap<=2
            return 'timing',hit,(round(mx,1),int(yy.min()),int(yy.max()),round(gap,1))
        return 'timing',False,None
    gray=fraction(button,(0,0,55),(179,60,255))
    if gray>.27:return 'waiting',False,None
    return 'unknown',False,None

@dataclass
class Controller:
    state:str='unknown'; candidate:str='unknown'; count:int=0; acted:bool=False; latch:bool=False; off:int=0; last:float=-99.; cycles:int=0; reward_pending:bool=False; reward_since:float=-1.; last_reward_click:float=-99.
    unknown_probe:bool=False; unknown_since:float=-1.; unknown_probed:bool=False
    target:tuple|None=None
    def step(self,state,hit,now,details=None):
        if state=='unknown':
            self.candidate='unknown';self.count=0
            # Optional single recovery tap after confirmed reeling/rewards.
            # Never rearm on a transient known frame; require a new cast/wait/bite.
            if self.unknown_since<0:self.unknown_since=now
            if (self.unknown_probe and not self.unknown_probed
                and self.state in ('timing','claim','dismiss','reward_wait')
                and now-self.unknown_since>=.5 and now-self.last>=.5):
                self.unknown_probed=True;self.last=now
                return 'unknown_probe'
            return None # preserve click latches, require fresh confirmation
        self.unknown_since=-1.
        if state==self.candidate:self.count+=1
        else:self.candidate=state;self.count=1
        if self.count<2:return None
        if state!=self.state:
            self.state=state;self.acted=False;self.latch=False;self.off=0;self.target=None
        if state in ('cast','waiting','bite'):
            self.unknown_probed=False
        if state in ("claim","dismiss","reward_wait"):
            if self.reward_since<0:self.reward_since=now
            self.reward_pending=True
            # Retry only on confirmed reward screens, not arbitrary unknown screens.
            ready=state=="claim" or now-self.reward_since>=.5
            if ready and now-self.last>=.5:
                self.last_reward_click=now;self.last=now
                return "claim" if state=="claim" else "dismiss"
            return None
        # Count a catch once the reward has actually cleared. Unknown frames
        # cannot clear the pending flag or trigger a blind tap.
        if self.reward_pending and state in ('cast','waiting','bite'):
            self.cycles+=1;self.reward_pending=False;self.reward_since=-1.
        elif not self.reward_pending:
            self.reward_since=-1.
        if state=='timing':
            if details is not None:
                zone=tuple(details[1:3])
                if self.target is not None and max(abs(zone[0]-self.target[0]),abs(zone[1]-self.target[1]))>12:
                    self.latch=False;self.off=0
                self.target=zone
            if not hit:
                self.off+=1
                if self.off>=2:self.latch=False
                return None
            self.off=0
            if not self.latch and now-self.last>=.22:
                self.latch=True;self.last=now;return 'timed_reel'
        elif state=='cast':
            # Retry missed cast clicks only while the green cast button is confirmed.
            if now-self.last >= .5:
                self.acted=True;self.last=now;return 'cast'
        elif state=='bite' and not self.acted and now-self.last>=.25:
            self.acted=True;self.last=now
            return state
        return None
