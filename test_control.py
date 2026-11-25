import socket
import struct
import threading
import unittest
from unittest.mock import Mock
from stream_backend import (TOUCH, touch_packet, send_tap, recv_exact,
                            read_video_header, StreamCapture, LatestFrames)

class ControlTests(unittest.TestCase):
    def test_down_wire_format(self):
        expected = bytes.fromhex('02 00 fffffffffffffffe 00000168 00000410 02d0 0500 ffff 00000000 00000000')
        self.assertEqual(touch_packet(0, 360, 1040, 720, 1280), expected)
        self.assertEqual(len(expected), 32)

    def test_up_wire_format(self):
        self.assertEqual(TOUCH.unpack(touch_packet(1, 360, 1040, 720, 1280)),
                         (2,1,2**64-2,360,1040,720,1280,0,0,0))

    def test_tap_single_write(self):
        sock = Mock()
        send_tap(sock, 360, 1125)
        sock.sendall.assert_called_once_with(touch_packet(0,360,1125,720,1280)+touch_packet(1,360,1125,720,1280))

    def test_reject_bad_coordinates(self):
        for x,y in [(-1,0),(720,0),(0,1280)]:
            with self.assertRaises(ValueError): send_tap(Mock(), x, y)

    def test_bad_action(self):
        with self.assertRaises(ValueError): touch_packet(2,0,0,720,1280)

    def test_fragmented_header(self):
        sock=Mock(); sock.recv.side_effect=[b'h',b'264',struct.pack('>II',720,1280)]
        self.assertEqual(read_video_header(sock),(720,1280))

    def test_wrong_dimensions(self):
        sock=Mock(); sock.recv.return_value=struct.pack('>III',0x68323634,704,1280)
        with self.assertRaisesRegex(RuntimeError,'--stream-input adb'): read_video_header(sock)

    def test_closed_handshake(self):
        sock=Mock(); sock.recv.side_effect=[b'h',b'']
        with self.assertRaises(EOFError): recv_exact(sock, 12)

    def test_failed_send_is_not_retried(self):
        stream=StreamCapture.__new__(StreamCapture)
        stream.control_sock=Mock(); stream.closed=threading.Event(); stream.control_error=None
        stream.control_sock.sendall.side_effect=OSError('connection reset')
        with self.assertRaisesRegex(RuntimeError,'no automatic retry'): stream.tap(360,1040)
        self.assertEqual(stream.control_sock.sendall.call_count,1)

    def test_control_loss_propagates(self):
        stream=StreamCapture.__new__(StreamCapture)
        stream.closed=threading.Event(); stream.latest=LatestFrames(); stream.control_error=None
        stream.control_sock=Mock(); stream.control_sock.recv.return_value=b''
        stream._drain_control()
        self.assertIsInstance(stream.control_error,EOFError)
        with self.assertRaisesRegex(RuntimeError,'control connection closed'): stream.latest.next(.01)
        with self.assertRaisesRegex(RuntimeError,'control unavailable'): stream.tap(360,1040)
        stream.control_sock.sendall.assert_not_called()

    def test_real_socket_roundtrip(self):
        a,b=socket.socketpair()
        with a,b:
            a.settimeout(1);b.settimeout(1)
            send_tap(a,360,1040)
            self.assertEqual(recv_exact(b,64),touch_packet(0,360,1040,720,1280)+touch_packet(1,360,1040,720,1280))
