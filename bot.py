"""BlueStacks foreground or local ADB automation. Dry-run by default."""
import argparse, ctypes, json, logging, math, sys, time
from pathlib import Path
from ctypes import wintypes
import cv2
import numpy as np
from vision import observe, Controller, locate, norm

ROOT=Path(__file__).resolve().parent
LOG=logging.getLogger('fishing')


class Windows:
    def __init__(self):
        if sys.platform!='win32': raise RuntimeError('Live capture requires Windows 10/11')
        self.u=ctypes.WinDLL('user32',use_last_error=True)
        self.k=ctypes.WinDLL('kernel32',use_last_error=True)
        u=self.u; k=self.k
        u.SetProcessDpiAwarenessContext.argtypes=[ctypes.c_void_p]
        u.SetProcessDpiAwarenessContext.restype=wintypes.BOOL
        if not u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            LOG.warning('Could not set DPI awareness; verify calibration visually')
        self.enum_cb=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        u.EnumWindows.argtypes=[self.enum_cb,wintypes.LPARAM]
        for name in ('IsWindow','IsWindowVisible','IsIconic'):
            getattr(u,name).argtypes=[wintypes.HWND]; getattr(u,name).restype=wintypes.BOOL
        u.GetWindowTextLengthW.argtypes=[wintypes.HWND]
        u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
        u.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        u.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)]
        u.GetForegroundWindow.restype=wintypes.HWND
        u.WindowFromPoint.argtypes=[wintypes.POINT]; u.WindowFromPoint.restype=wintypes.HWND
        u.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]; u.GetAncestor.restype=wintypes.HWND
        u.GetAsyncKeyState.argtypes=[ctypes.c_int]; u.GetAsyncKeyState.restype=ctypes.c_short
        u.SetCursorPos.argtypes=[ctypes.c_int,ctypes.c_int]; u.SetCursorPos.restype=wintypes.BOOL
        u.mouse_event.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.c_size_t]
        k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; k.OpenProcess.restype=wintypes.HANDLE
        k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        k.CloseHandle.argtypes=[wintypes.HANDLE]

    def find(self, query):
        found=[]; u=self.u; k=self.k
        @self.enum_cb
        def visit(hwnd,_):
            if not u.IsWindowVisible(hwnd): return True
            buf=ctypes.create_unicode_buffer(u.GetWindowTextLengthW(hwnd)+1); u.GetWindowTextW(hwnd,buf,len(buf))
            pid=wintypes.DWORD(); u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            proc=k.OpenProcess(0x1000,False,pid.value)
            if proc:
                try:
                    size=wintypes.DWORD(32768); exe=ctypes.create_unicode_buffer(size.value)
                    if k.QueryFullProcessImageNameW(proc,0,exe,ctypes.byref(size)) and Path(exe.value).name.lower()=='hd-player.exe' and query.lower() in buf.value.lower():
                        found.append((hwnd,buf.value))
                finally: k.CloseHandle(proc)
            return True
        u.EnumWindows(visit,0)
        if len(found)!=1: raise RuntimeError(f'Expected one matching HD-Player window, found {found}. Set window_title to a unique title in config.json.')
        LOG.info('Target: %s',found[0][1]); return found[0][0]

    def rect(self,hwnd):
        u=self.u; r=wintypes.RECT(); p=wintypes.POINT(0,0)
        if not u.IsWindow(hwnd) or u.IsIconic(hwnd) or not u.GetClientRect(hwnd,ctypes.byref(r)) or not u.ClientToScreen(hwnd,ctypes.byref(p)):
            raise RuntimeError('Target unavailable or minimized')
        if r.right<=0 or r.bottom<=0: raise RuntimeError('Empty target window')
        return {'left':p.x,'top':p.y,'width':r.right,'height':r.bottom}

    def active(self,hwnd): return self.u.GetForegroundWindow()==hwnd
    def stop(self): return bool(self.u.GetAsyncKeyState(0x77)&0x8000)  # F8
    def click(self,hwnd,x,y,original_rect):
        u=self.u
        if self.stop() or not self.active(hwnd) or self.rect(hwnd)!=original_rect: return False
        if u.GetAncestor(u.WindowFromPoint(wintypes.POINT(x,y)),2)!=hwnd: return False
        if not u.SetCursorPos(x,y): return False
        if self.stop() or not self.active(hwnd): return False
        u.mouse_event(0x0002,0,0,0,0); u.mouse_event(0x0004,0,0,0,0)
        return True


def countdown(win,hwnd):
    LOG.info('Focus BlueStacks now. F8 or Ctrl+C stops the program.')
    for _ in range(50):
        if win.stop(): raise KeyboardInterrupt
        time.sleep(.1)
    if not win.active(hwnd): raise RuntimeError('BlueStacks must be the foreground window')


def capture(sct,rect): return np.asarray(sct.grab(rect))[:,:,:3].copy()


def overlay(frame, viewport):
    img=frame.copy(); l,t,r,b=viewport
    cv2.rectangle(img,(l,t),(r-1,b-1),(0,255,0),2)
    def pt(x,y):return (round(l+x/720*(r-l)),round(t+y/1280*(b-t)))
    cv2.rectangle(img,pt(195,830),pt(560,872),(0,255,255),2)
    cv2.circle(img,pt(360,1040),7,(255,255,255),2)
    cv2.circle(img,pt(360,1125),7,(0,255,0),2)
    return img


def analyze(frame,viewport):return observe(norm(frame,viewport))


def replay(path):
    cap=cv2.VideoCapture(str(path)); fps=cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps<=0:raise ValueError('Cannot open recording')
    c=Controller(); previous=None; i=0; n=0; viewport=None
    while True:
        ok,frame=cap.read()
        if not ok:break
        if viewport is None:viewport=locate(frame); LOG.info('Viewport: %s',viewport)
        state,hit,details=analyze(frame,viewport); now=i/fps
        if state!=previous:LOG.info('%.2fs State: %s',now,state);previous=state
        action=c.step(state,hit,now)
        if action:n+=1;LOG.info('%.2fs WOULD CLICK %s %s',now,action,details or '')
        i+=1
    cap.release(); LOG.info('Replay: %d frames, %d proposed clicks, %d claims',i,n,c.cycles)


def adb_main(args):
    from adb_backend import ADB
    from timing import TimingLead
    adb=ADB(args.adb_path,args.serial,args.capture_mode)
    if args.backend=='stream':
        from stream_backend import StreamCapture
        # Query original Android dimensions once; stream frames use normalized size.
        physical=adb.capture(); ph,pw=physical.shape[:2]
        if abs(pw/ph-720/1280)>.025:raise RuntimeError('Expected portrait 9:16 Android screen')
        with StreamCapture(adb,args.scrcpy_server,args.ffmpeg_path,args.stream_fps,args.stream_bitrate) as stream:
            return adb_loop(args,adb,stream,(pw,ph))
    return adb_loop(args,adb,adb)


def adb_loop(args,adb,source,physical_size=None):
    from timing import TimingLead
    tracker=TimingLead()
    streaming=args.backend=='stream'
    win=Windows() if sys.platform=='win32' else None
    stop=lambda: win is not None and win.stop()
    frame=source.capture(); h,w=frame.shape[:2]
    pw,ph=physical_size or (w,h)
    if abs(w/h-720/1280)>.025:raise RuntimeError(f'Expected portrait 9:16 Android screen, got {w}x{h}')
    viewport=(0,0,w,h)
    LOG.info('ADB device %s: %dx%d, capture %s',args.serial,w,h,source.mode)
    if args.snapshot:
        cv2.imwrite(str(ROOT/('stream-snapshot.png' if streaming else 'adb-snapshot.png')),frame);return
    if args.benchmark:
        times=[]
        for _ in range(60 if streaming else 15):
            t=time.monotonic();source.capture();times.append(time.monotonic()-t)
        LOG.info('%s median %.0f ms; p95 %.0f ms; %.1f FPS (capture only)', 'Fresh-frame interval (not end-to-end latency)' if streaming else 'Capture', np.median(times)*1000,np.percentile(times,95)*1000,1/np.mean(times));return
    initial=analyze(frame,viewport)[0]
    if initial not in ('cast','waiting','bite','timing','claim','dismiss','reward_wait'):
        raise RuntimeError('Fishing screen not recognised. Open Fishing Contest first.')
    if args.live and initial=='timing':raise RuntimeError('Start live mode before casting or while waiting, not during timed reeling.')
    LOG.info('%s %s mode; F8 or Ctrl+C stops. Limits: %d catches / %ds', 'LIVE' if args.live else 'DRY RUN', 'SCRCPY' if streaming else 'ADB',args.max_catches,args.max_seconds)
    controller=Controller(unknown_probe=args.unknown_probe); start=time.monotonic();last_known=start;n=0;previous=None
    tap_ms=None
    LOG.info("ADB timing lead: %s", "auto" if args.timing_lead_ms is None else f"{args.timing_lead_ms:.0f} ms")
    while not stop() and controller.cycles<args.max_catches and time.monotonic()-start<args.max_seconds:
        t=time.monotonic();frame=source.capture();now=time.monotonic()
        if stop() or now-start>=args.max_seconds:break
        if frame.shape[:2]!=(h,w):raise RuntimeError('Android resolution changed; stopping')
        state,hit,details=analyze(frame,viewport)
        if state!='unknown':last_known=now
        if state!=previous:LOG.info('State: %s',state);previous=state
        if now-last_known>8:LOG.warning('Unknown screen timeout');break
        capture_ms=(now-t)*1000
        # Capture time is a rough proxy for frame age; the tap command's full
        # duration is an upper bound on delivery delay, not a measurement of it.
        stamp=source.stamp if streaming else (t+now)/2
        estimated_age=args.stream_latency_ms if streaming else capture_ms*.5
        lead=args.timing_lead_ms if args.timing_lead_ms is not None else max(0, estimated_age + (tap_ms*.5 if tap_ms is not None else 40) + (time.monotonic()-(stamp if streaming else now))*1000)
        hit,prediction=tracker.step(state,hit,details,stamp,lead)
        action=controller.step(state,hit,time.monotonic())
        if controller.cycles>=args.max_catches:break
        if action:
            px,py=(360,1125) if action=='claim' else (360,1040)
            if stop():break
            if args.live:
                tap_start=time.monotonic();adb.tap(round(px/720*pw),round(py/1280*ph))
                elapsed=(time.monotonic()-tap_start)*1000
                tap_ms=elapsed if tap_ms is None else .7*tap_ms+.3*elapsed
            n+=1;LOG.info('%s %s (#%d) %s [capture %.0fms, tap %s, lead %.0fms, prediction %s]', 'CLICK' if args.live else 'WOULD CLICK',action,n,details or '',capture_ms, f'{tap_ms:.0f}ms' if tap_ms is not None else 'n/a',lead,prediction or 'n/a')
        time.sleep(.008)
    LOG.info('Stopped: %d clicks, %d reward screens counted',n,controller.cycles)


def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--snapshot',action='store_true');p.add_argument('--image',type=Path);p.add_argument('--replay',type=Path);p.add_argument('--max-catches',type=int,default=3);p.add_argument('--max-seconds',type=int,default=180);p.add_argument("--backend",choices=("window","adb","stream"),default="window");p.add_argument("--serial",default="127.0.0.1:5555");p.add_argument("--adb-path");p.add_argument("--capture-mode",choices=("raw","png"),default="raw");p.add_argument("--benchmark",action="store_true");p.add_argument("--timing-lead-ms",type=float,help="ADB timing lead in milliseconds (default: automatic; 0 disables prediction)");p.add_argument("--unknown-probe",action="store_true",help="One experimental recovery tap after a persistent unknown screen following reeling or rewards");p.add_argument('--scrcpy-server');p.add_argument('--ffmpeg-path');p.add_argument('--stream-fps',type=int,default=60);p.add_argument('--stream-bitrate',type=int,default=8000000);p.add_argument('--stream-latency-ms',type=float,default=35,help='Estimated video transport delay for automatic timing lead (not measured)');args=p.parse_args()
    if not 1<=args.stream_fps<=120 or args.stream_bitrate<100000 or not math.isfinite(args.stream_latency_ms) or args.stream_latency_ms<0:p.error('Invalid stream settings')
    if args.timing_lead_ms is not None and (not math.isfinite(args.timing_lead_ms) or args.timing_lead_ms<0):p.error("Timing lead must be a finite nonnegative number")
    if args.max_catches<1 or args.max_seconds<1:p.error('Limits must be positive')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',handlers=[logging.StreamHandler(),logging.FileHandler(ROOT/'bot.log',encoding='utf-8')]);
    if args.replay:replay(args.replay);return
    if args.image:
        frame=cv2.imread(str(args.image))
        if frame is None:raise ValueError('Cannot read image')
        viewport=(0,0,frame.shape[1],frame.shape[0]) if abs(frame.shape[1]/frame.shape[0]-720/1280)<.025 else locate(frame);LOG.info('Viewport: %s; detected: %s',viewport,analyze(frame,viewport));cv2.imwrite(str(ROOT/'preview.png'),overlay(frame,viewport));return
    if args.backend in ("adb","stream"):adb_main(args);return
    win=Windows();import mss
    hwnd=win.find('BlueStacks');countdown(win,hwnd)
    factory=getattr(mss,'MSS',None) or mss.mss
    with factory() as sct:
        rect=win.rect(hwnd);frame=capture(sct,rect);viewport=locate(frame);LOG.info('Viewport: %s',viewport)
        if args.snapshot:
            cv2.imwrite(str(ROOT/'snapshot.png'),frame);cv2.imwrite(str(ROOT/'preview.png'),overlay(frame,viewport));return
        LOG.info('%s mode; max %d claims or %d seconds; F8 stops.', 'LIVE' if args.live else 'DRY RUN',args.max_catches,args.max_seconds)
        controller=Controller(unknown_probe=args.unknown_probe); start=time.monotonic();last_known=start;n=0;previous=None
        while not win.stop() and controller.cycles<args.max_catches and time.monotonic()-start<args.max_seconds:
            if not win.active(hwnd) or win.rect(hwnd)!=rect:LOG.warning('Target focus or position changed; stopping');break
            frame=capture(sct,rect);state,hit,details=analyze(frame,viewport);now=time.monotonic()
            if state!='unknown':last_known=now
            if state!=previous:LOG.info('State: %s',state);previous=state
            if now-last_known>8:LOG.warning('Unknown screen timeout');break
            action=controller.step(state,hit,now)
            if controller.cycles>=args.max_catches:break
            if action:
                l,t,r,b=viewport;px,py=(360,1125) if action=='claim' else (360,1040)
                x=rect['left']+round(l+px/720*(r-l));y=rect['top']+round(t+py/1280*(b-t))
                if args.live and not win.click(hwnd,x,y,rect):LOG.warning('Click safety check failed; stopping');break
                n+=1;LOG.info('%s %s (#%d) %s','CLICK' if args.live else 'WOULD CLICK',action,n,details or '')
            time.sleep(.008)
        LOG.info('Stopped: %d %s, %d claims',n,'clicks' if args.live else 'simulated clicks',controller.cycles)

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:LOG.info('Stopped by user')
    except Exception as e:LOG.error('%s',e);sys.exit(1)
