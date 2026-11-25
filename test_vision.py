import unittest,struct
import numpy as np
from vision import Controller, observe, norm
from adb_backend import decode_raw
import cv2
from pathlib import Path
class Tests(unittest.TestCase):
    def test_cast_retry(self):
        c=Controller();self.assertIsNone(c.step('cast',False,0));self.assertEqual(c.step('cast',False,.03),'cast');self.assertIsNone(c.step('cast',False,.50));self.assertEqual(c.step('cast',False,.54),'cast')
    def test_waiting(self):
        c=Controller();c.step('waiting',False,0);self.assertIsNone(c.step('waiting',False,1))
    def test_timing_latch(self):
        c=Controller();c.step('timing',True,0);self.assertEqual(c.step('timing',True,.04),'timed_reel');self.assertIsNone(c.step('timing',True,1));c.step('timing',False,1.1);c.step('timing',False,1.2);self.assertEqual(c.step('timing',True,1.3),'timed_reel')
    def test_claim_retry_counts_on_exit(self):
        c=Controller();c.step('claim',False,0);self.assertEqual(c.step('claim',False,.03),'claim');self.assertIsNone(c.step('claim',False,.5));self.assertEqual(c.step('claim',False,.54),'claim');self.assertEqual(c.cycles,0)
        c.step('cast',False,1);self.assertEqual(c.step('cast',False,1.05),'cast');self.assertEqual(c.cycles,1)
    def test_dismiss(self):
        c=Controller();c.step('dismiss',False,0);self.assertIsNone(c.step('dismiss',False,.03));self.assertEqual(c.step('dismiss',False,.54),'dismiss');self.assertIsNone(c.step('dismiss',False,.99));self.assertEqual(c.step('dismiss',False,1.05),'dismiss');self.assertEqual(c.cycles,0)
        c.step('cast',False,1.6);c.step('cast',False,1.65);self.assertEqual(c.cycles,1)
    def test_reward_wait_fallback(self):
        c=Controller();c.step('reward_wait',False,0);c.step('reward_wait',False,.03);self.assertIsNone(c.step('reward_wait',False,.5));self.assertEqual(c.step('reward_wait',False,.54),'dismiss')
    def test_reward_transition_count(self):
        c=Controller();c.step('claim',False,0);c.step('claim',False,.03);self.assertIsNone(c.step('unknown',False,.8));c.step('dismiss',False,1);c.step('dismiss',False,1.2);self.assertEqual(c.cycles,0);c.step('cast',False,2);c.step('cast',False,2.1);self.assertEqual(c.cycles,1);c.step('claim',False,3);c.step('claim',False,3.1);c.step('waiting',False,4);c.step('waiting',False,4.1);self.assertEqual(c.cycles,2)
    def test_retry_stops_when_casted(self):
        c=Controller();c.step('cast',False,0);c.step('cast',False,.03);c.step('waiting',False,.2);self.assertIsNone(c.step('waiting',False,.6));self.assertIsNone(c.step('waiting',False,2))
    def test_no_blind_taps(self):
        c=Controller();c.step('dismiss',False,0);c.step('dismiss',False,.03);c.step('dismiss',False,.6);self.assertIsNone(c.step('unknown',False,2));self.assertIsNone(c.step('unknown',False,3))
    def test_unknown_probe_once(self):
        c=Controller(unknown_probe=True)
        c.step('timing',False,0);c.step('timing',False,.1)
        self.assertIsNone(c.step('unknown',False,.2))
        self.assertEqual(c.step('unknown',False,.75),'unknown_probe')
        self.assertIsNone(c.step('unknown',False,1.5))
        c.step('timing',False,2);c.step('timing',False,2.1)
        c.step('unknown',False,2.2);self.assertIsNone(c.step('unknown',False,3))
        self.assertEqual(c.cycles,0)
        c.step('cast',False,4);c.step('cast',False,4.1)
        c.step('timing',False,5);c.step('timing',False,5.1)
        c.step('unknown',False,5.2);self.assertEqual(c.step('unknown',False,6),'unknown_probe')
    def test_unknown_probe_not_waiting(self):
        for state in ('cast','waiting','bite'):
            c=Controller(unknown_probe=True);c.step(state,False,0);c.step(state,False,.1)
            self.assertIsNone(c.step('unknown',False,1));self.assertIsNone(c.step('unknown',False,2))
    def test_unknown_probe_opt_in(self):
        c=Controller();c.step('timing',False,0);c.step('timing',False,.1)
        c.step('unknown',False,1);self.assertIsNone(c.step('unknown',False,2))
    def test_raw(self):
        pixels=bytes([10,20,30,255,40,50,60,255]);header=struct.pack('<III',2,1,1)
        for data in (header+pixels,header+bytes(4)+pixels):
            self.assertEqual(decode_raw(data).tolist(),[[[30,20,10],[60,50,40]]])
    def test_truncated_raw(self):
        with self.assertRaises(ValueError):decode_raw(b'abc')
if __name__=='__main__':unittest.main()

class NarrowTargetTests(unittest.TestCase):
    def test_new_zone_rearms_latch(self):
        c=Controller();c.step('timing',True,0,(340,320,350,0));self.assertEqual(c.step('timing',True,.03,(340,320,350,0)),'timed_reel')
        self.assertEqual(c.step('timing',True,.3,(465,454,475,0)),'timed_reel')
