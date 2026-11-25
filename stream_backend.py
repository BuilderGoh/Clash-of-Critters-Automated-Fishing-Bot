"""Pinned scrcpy 3.3.4 video-only transport with a latest-frame FFmpeg decoder."""
import logging, os, secrets, shutil, socket, subprocess, threading, time
from pathlib import Path
import numpy as np

LOG = logging.getLogger('fishing')
ROOT = Path(__file__).resolve().parent
VERSION = '3.3.4'
WIDTH, HEIGHT = 720, 1280
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def find_server(path=None):
    candidates = [Path(path)] if path else [ROOT / 'scrcpy-server-v3.3.4', ROOT / 'scrcpy-server', ROOT / 'scrcpy' / 'scrcpy-server']
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise RuntimeError('Missing scrcpy 3.3.4 server. See STREAM-README.txt; use --scrcpy-server to specify its path.')


def find_ffmpeg(path=None):
    candidate = path or shutil.which('ffmpeg') or str(ROOT / 'ffmpeg.exe')
    if Path(candidate).is_file() or shutil.which(candidate):
        return candidate
    raise RuntimeError('FFmpeg not found. Install FFmpeg, reopen CMD, or use --ffmpeg-path.')


def read_exact(source, n):
    data = bytearray(n)
    view = memoryview(data)
    pos = 0
    while pos < n:
        count = source.readinto(view[pos:])
        if not count:
            raise EOFError('Video decoder closed its output')
        pos += count
    return data


def decoder_command(ffmpeg):
    return [ffmpeg, '-hide_banner', '-loglevel', 'warning', '-nostdin',
            '-probesize', '32', '-analyzeduration', '0', '-flags', 'low_delay',
            '-threads', '1', '-f', 'h264', '-i', 'pipe:0', '-an', '-sn',
            '-vf', 'scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2',
            '-pix_fmt', 'bgr24', '-threads', '1', '-fps_mode', 'passthrough',
            '-flush_packets', '1', '-f', 'rawvideo', 'pipe:1']


def forwarded_port(adb, remote):
    """Find a forward belonging to this device and unique server socket."""
    for line in adb.run('forward', '--list').decode(errors='replace').splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == adb.serial and fields[2] == remote:
            local = fields[1]
            if local.startswith('tcp:') and local[4:].isdigit():
                port = int(local[4:])
                if 1 <= port <= 65535:
                    return port
    return None


def allocate_forward(adb, remote):
    """Support older ADB builds that omit the dynamically allocated port."""
    try:
        response = adb.run('forward', 'tcp:0', remote).strip()
        if response.isdigit() and 1 <= int(response) <= 65535:
            return int(response)
    except RuntimeError as exc:
        LOG.debug('Dynamic ADB forwarding unsupported: %s', exc)
    port = forwarded_port(adb, remote)
    if port is not None:
        LOG.info('Recovered ADB forwarding port %d from forward list', port)
        return port
    # Ask the OS for an available loopback port, then request it explicitly.
    # The socket must be released before ADB can bind; no-rebind prevents
    # replacing an existing ADB forward in the small allocation race window.
    last_error = None
    for _ in range(5):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
            reservation.bind(('127.0.0.1', 0))
            candidate = reservation.getsockname()[1]
        try:
            adb.run('forward', '--no-rebind', f'tcp:{candidate}', remote)
            actual = forwarded_port(adb, remote)
            if actual == candidate:
                LOG.info('Using explicit ADB forwarding port %d', actual)
                return actual
            if actual is not None:
                return actual
            last_error = 'ADB did not list the requested forward'
        except RuntimeError as exc:
            last_error = str(exc)
    raise RuntimeError(f'Cannot allocate ADB video forwarding port: {last_error}. '
                       'Check HD-Adb.exe forward --list and adb version.')


class LatestFrames:
    def __init__(self):
        self.condition = threading.Condition()
        self.frame = None
        self.seq = 0
        self.stamp = None
        self.error = None
        self.consumed = 0

    def publish(self, frame):
        with self.condition:
            self.frame = frame
            self.stamp = time.monotonic()
            self.seq += 1
            self.condition.notify_all()

    def fail(self, error):
        with self.condition:
            if self.error is None:
                self.error = error
            self.condition.notify_all()

    def next(self, timeout=5):
        with self.condition:
            if not self.condition.wait_for(lambda: self.error is not None or self.seq > self.consumed, timeout):
                raise RuntimeError('No new stream frame; stopping instead of using a stale image')
            if self.error is not None:
                raise RuntimeError(f'Stream ended: {self.error}')
            self.consumed = self.seq
            return self.frame, self.stamp


class StreamCapture:
    def __init__(self, adb, server=None, ffmpeg=None, max_fps=60, bitrate=8_000_000):
        self.adb = adb
        self.server = find_server(server)
        self.ffmpeg = find_ffmpeg(ffmpeg)
        self.max_fps = max_fps
        self.bitrate = bitrate
        self.mode = 'scrcpy'
        self.port = None
        self.remote = None
        self.proc = self.decoder = self.sock = None
        self.threads = []
        self.closed = threading.Event()
        self.latest = LatestFrames()
        self.stamp = None
        self.logfiles = []

    def __enter__(self):
        try:
            self.start()
            return self
        except BaseException:
            self.close()
            raise

    def __exit__(self, *exc):
        self.close()

    def start(self):
        scid = f'{secrets.randbits(31):08x}'
        self.remote = f'/data/local/tmp/critters-scrcpy-{scid}.jar'
        self.adb.run('push', str(self.server), self.remote, timeout=30)
        self.port = allocate_forward(self.adb, 'localabstract:scrcpy_' + scid)
        LOG.info('ADB video forwarding port: %d', self.port)
        server_log = open(ROOT / 'scrcpy-server.log', 'wb')
        self.logfiles.append(server_log)
        command = [self.adb.exe, '-s', self.adb.serial, 'shell', 'CLASSPATH=' + self.remote,
                   'app_process', '/', 'com.genymobile.scrcpy.Server', VERSION,
                   'scid=' + scid, 'log_level=info', 'tunnel_forward=true', 'audio=false',
                   'control=false', 'cleanup=false', 'raw_stream=true', 'video_codec=h264',
                   'max_size=1280', 'max_fps=' + str(self.max_fps), 'video_bit_rate=' + str(self.bitrate)]
        self.proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=server_log,
                                     stderr=subprocess.STDOUT, creationflags=FLAGS)
        # The ADB forward may exist before the Android server starts listening.
        deadline = time.monotonic() + 12
        first = b''
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError('scrcpy server exited; inspect scrcpy-server.log')
            s = None
            try:
                s = socket.create_connection(('127.0.0.1', self.port), timeout=1)
                s.settimeout(3)
                first = s.recv(65536)
                if first:
                    self.sock = s
                    s.settimeout(5)
                    break
            except (OSError, TimeoutError):
                pass
            if s is not None:
                s.close()
            time.sleep(.15)
        if self.sock is None:
            raise RuntimeError('Cannot receive scrcpy video; inspect scrcpy-server.log')
        decoder_log = open(ROOT / 'scrcpy-decoder.log', 'wb')
        self.logfiles.append(decoder_log)
        self.decoder = subprocess.Popen(decoder_command(self.ffmpeg), stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=decoder_log, bufsize=0, creationflags=FLAGS)
        self.threads = [threading.Thread(target=self._feed, args=(first,), daemon=True),
                        threading.Thread(target=self._decode, daemon=True)]
        for thread in self.threads:
            thread.start()

    def _feed(self, first):
        try:
            data = first
            while data and not self.closed.is_set():
                view = memoryview(data)
                while view:
                    n = self.decoder.stdin.write(view)
                    if not n:
                        raise EOFError('FFmpeg stopped accepting video')
                    view = view[n:]
                data = self.sock.recv(65536)
            if not self.closed.is_set():
                raise EOFError('scrcpy video socket closed')
        except Exception as exc:
            if not self.closed.is_set():
                self.latest.fail(exc)
        finally:
            try:
                self.decoder.stdin.close()
            except OSError:
                pass

    def _decode(self):
        try:
            while not self.closed.is_set():
                data = read_exact(self.decoder.stdout, WIDTH * HEIGHT * 3)
                self.latest.publish(np.frombuffer(data, dtype=np.uint8).reshape(HEIGHT, WIDTH, 3))
        except Exception as exc:
            if not self.closed.is_set():
                self.latest.fail(exc)

    def capture(self):
        frame, self.stamp = self.latest.next(timeout=8 if self.stamp is None else 5)
        return frame

    def close(self):
        if self.closed.is_set():
            return
        self.closed.set()
        self.latest.fail('closed')
        if self.sock is not None:
            try: self.sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            self.sock.close()
        for proc in (self.decoder, self.proc):
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    try: proc.kill(); proc.wait(timeout=2)
                    except (OSError, subprocess.TimeoutExpired): pass
        for thread in self.threads:
            thread.join(timeout=1)
        for proc in (self.decoder, self.proc):
            if proc is not None:
                for pipe in (proc.stdin, proc.stdout):
                    if pipe is not None:
                        try: pipe.close()
                        except OSError: pass
        if self.port is not None:
            try: self.adb.run('forward', '--remove', f'tcp:{self.port}')
            except Exception: LOG.warning('Could not remove stream forwarding port %s', self.port)
        if self.remote is not None:
            try: self.adb.run('shell', 'rm', '-f', self.remote)
            except Exception: LOG.warning('Could not remove temporary scrcpy server')
        for log in self.logfiles:
            log.close()
