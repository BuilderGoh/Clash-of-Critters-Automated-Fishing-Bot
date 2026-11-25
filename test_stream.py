import io, unittest, time
import numpy as np
from stream_backend import LatestFrames, read_exact, decoder_command

class StreamTests(unittest.TestCase):
    def test_read_exact(self):
        self.assertEqual(read_exact(io.BytesIO(b'abcdef'), 4), b'abcd')
    def test_truncated(self):
        with self.assertRaises(EOFError): read_exact(io.BytesIO(b'abc'), 4)
    def test_latest_not_queue(self):
        buf=LatestFrames();buf.publish('first');buf.publish('second');buf.publish('latest')
        self.assertEqual(buf.next(.01)[0], 'latest')
    def test_no_reuse(self):
        buf=LatestFrames();buf.publish(1);buf.next(.01)
        with self.assertRaises(RuntimeError):buf.next(.01)
    def test_failure(self):
        buf=LatestFrames();buf.publish(1);buf.fail('lost connection')
        with self.assertRaisesRegex(RuntimeError,'lost connection'):buf.next(.01)
    def test_timestamp(self):
        buf=LatestFrames();start=time.monotonic();buf.publish(1);_,stamp=buf.next(.01)
        self.assertGreaterEqual(stamp,start)
    def test_decoder_raw_output(self):
        cmd=decoder_command('ffmpeg');self.assertEqual(cmd[-3:],['-f','rawvideo','pipe:1']);self.assertIn('bgr24',cmd)

class ForwardTests(unittest.TestCase):
    def fake(self, replies):
        from unittest.mock import Mock
        adb = Mock(serial='127.0.0.1:5555')
        adb.run.side_effect = replies
        return adb

    def test_dynamic_port_response(self):
        from stream_backend import allocate_forward
        self.assertEqual(allocate_forward(self.fake([b'27183\n']), 'localabstract:scrcpy_test'), 27183)

    def test_empty_response_recovers_listed_port(self):
        from stream_backend import allocate_forward
        adb = self.fake([b'', b'127.0.0.1:5555 tcp:27184 localabstract:scrcpy_test\n'])
        self.assertEqual(allocate_forward(adb, 'localabstract:scrcpy_test'), 27184)

    def test_empty_response_explicit_port(self):
        from unittest.mock import Mock
        from stream_backend import allocate_forward
        adb = Mock(serial='127.0.0.1:5555')
        state = {}
        def run(*args):
            if args == ('forward','tcp:0','localabstract:scrcpy_test'): return b''
            if args == ('forward','--list'):
                return ('127.0.0.1:5555 '+state['port']+' localabstract:scrcpy_test\n').encode() if state else b''
            if args[:2] == ('forward','--no-rebind'):
                state['port'] = args[2]; return b''
            raise AssertionError(args)
        adb.run.side_effect = run
        self.assertEqual(allocate_forward(adb, 'localabstract:scrcpy_test'), int(state['port'][4:]))

    def test_ignores_other_device_and_remote(self):
        from stream_backend import forwarded_port
        adb = self.fake([b'127.0.0.1:5556 tcp:27185 localabstract:scrcpy_test\n127.0.0.1:5555 tcp:27186 localabstract:unrelated\n'])
        self.assertIsNone(forwarded_port(adb, 'localabstract:scrcpy_test'))

    def test_dynamic_failure_recovers_list(self):
        from stream_backend import allocate_forward
        adb = self.fake([RuntimeError('unsupported'), b'127.0.0.1:5555 tcp:27187 localabstract:scrcpy_test\n'])
        self.assertEqual(allocate_forward(adb, 'localabstract:scrcpy_test'), 27187)
