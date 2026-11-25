"""Local BlueStacks ADB capture and input. No physical mouse movement."""
import os, shutil, subprocess, struct, time, ipaddress
from pathlib import Path
import cv2
import numpy as np


def decode_raw(data):
    if len(data)<12:raise ValueError('Truncated raw screenshot')
    w,h,fmt=struct.unpack_from('<III',data)
    if not (0<w<=8192 and 0<h<=8192):raise ValueError('Invalid screenshot dimensions')
    channels={1:4,2:4,3:3}.get(fmt)
    if channels is None:raise ValueError(f'Unsupported pixel format {fmt}')
    offset=len(data)-w*h*channels
    if offset not in (12,16):raise ValueError('Unexpected raw screenshot length')
    pixels=np.frombuffer(data,dtype=np.uint8,offset=offset).reshape(h,w,channels)
    return cv2.cvtColor(pixels,cv2.COLOR_RGBA2BGR if channels==4 else cv2.COLOR_RGB2BGR)

class ADB:
    def __init__(self,path,serial,capture_mode='raw'):
        if path:
            self.exe=path
        else:
            candidates=[Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'BlueStacks_nxt'/'HD-Adb.exe',Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'BlueStacks'/'HD-Adb.exe']
            self.exe=next((str(p) for p in candidates if p.is_file()),None) or shutil.which('adb')
        if not self.exe:raise RuntimeError('ADB not found. Use --adb-path with the full HD-Adb.exe path.')
        try:
            host,port=serial.rsplit(':',1)
            if not ipaddress.ip_address(host).is_loopback or not 1<=int(port)<=65535:raise ValueError()
        except ValueError:raise RuntimeError('Use the local BlueStacks address, e.g. 127.0.0.1:5555')
        self.serial=serial;self.mode=capture_mode
        self.run('connect',serial,device=False)
        if self.run('get-state').strip()!=b'device':raise RuntimeError('ADB device not ready; check BlueStacks Advanced settings.')
    def run(self,*args,device=True,timeout=5):
        command=[self.exe]+(['-s',self.serial] if device else [])+list(args)
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace').strip() or str(command))
        return result.stdout
    def capture(self):
        if self.mode=='raw':
            try:return decode_raw(self.run('exec-out','screencap'))
            except ValueError:self.mode='png'
        frame=cv2.imdecode(np.frombuffer(self.run('exec-out','screencap','-p'),np.uint8),cv2.IMREAD_COLOR)
        if frame is None:raise RuntimeError('Cannot decode ADB screenshot')
        return frame
    def tap(self,x,y):self.run('shell','input','tap',str(x),str(y))
