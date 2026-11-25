import unittest
import numpy as np
from vision import timing_observation, Controller
from timing import TimingLead

class VisionNarrow(unittest.TestCase):
    def frame(self, x=310):
        a=np.zeros((1280,720,3),np.uint8)
        a[835:855,x-7:x+7]=(2,220,210)
        return a
    def test_single_column(self):
        a=self.frame();a[851:871,350]=(30,220,245)
        self.assertEqual(timing_observation(a)[2][1:3],(350,350))
    def test_compressed_strip(self):
        a=self.frame();a[850:872,350:352]=(30,100,190);a[851:855,350:352]=(30,180,220)
        self.assertEqual(timing_observation(a)[2][1:3],(350,351))
    def test_isolated_noise_rejected(self):
        a=self.frame();a[850:852,350]=(30,220,245)
        self.assertEqual(timing_observation(a)[2][1:3],(None,None))
    def test_no_marker_no_click(self):
        a=np.zeros((1280,720,3),np.uint8);a[850:872,350]=(30,220,245)
        self.assertEqual(timing_observation(a),('timing',False,None))
    def test_unrelated_runs_not_joined(self):
        a=self.frame();a[850:872,350:358]=(30,220,245);a[850:872,400:402]=(30,220,245)
        self.assertEqual(timing_observation(a)[2][1:3],(350,357))
    def test_marker_gap_joined(self):
        a=self.frame(350);a[850:872,330:342]=(30,220,245);a[850:872,358:370]=(30,220,245)
        self.assertEqual(timing_observation(a)[2][1:3],(330,369))

class TimingNarrow(unittest.TestCase):
    def test_single_pixel_target(self):
        t=TimingLead();t.step('timing',False,(290,310,310,20),0,50)
        self.assertTrue(t.step('timing',False,(300,310,310,10),.05,50)[0])
    def test_occlusion(self):
        t=TimingLead();t.step('timing',False,(295,310,311,15),0,0)
        self.assertTrue(t.step('timing',False,(310,None,None,None),.05,0)[0])
        self.assertEqual(t.resolved_details[1:3],(310,311))
    def test_occlusion_expires(self):
        t=TimingLead();t.step('timing',False,(295,310,311,15),0,0)
        self.assertFalse(t.step('timing',False,(310,None,None,None),.13,0)[0])
    def test_occlusion_not_near(self):
        t=TimingLead();t.step('timing',False,(295,310,311,15),0,0)
        self.assertFalse(t.step('timing',False,(350,None,None,None),.05,0)[0])
    def test_no_reuse_after_tap(self):
        t=TimingLead();t.step('timing',True,(310,310,311,0),0,0);t.note_click()
        self.assertFalse(t.step('timing',False,(310,None,None,None),.05,0)[0])
    def test_nearest_frame_tolerance(self):
        t=TimingLead();t.step('timing',False,(289,310,311,21),0,40)
        self.assertTrue(t.step('timing',False,(296,310,311,14),.02,35)[0])
    def test_no_zone_no_tap(self):
        t=TimingLead();self.assertFalse(t.step('timing',False,(310,None,None,None),0,40)[0])
    def test_latch_small_disjoint_zone(self):
        c=Controller();c.step('timing',True,0,(310,310,311,0));self.assertEqual(c.step('timing',True,.03,(310,310,311,0)),'timed_reel');self.assertEqual(c.step('timing',True,.26,(316,316,317,0)),'timed_reel')
    def test_partial_occlusion(self):
        t=TimingLead();t.step('timing',False,(290,310,330,20),0,0)
        self.assertTrue(t.step('timing',False,(311,326,330,15),.05,0)[0])
        self.assertEqual(t.resolved_details[1:3],(310,330))
    def test_duplicate_frame_retains_velocity(self):
        t=TimingLead();t.step('timing',False,(280,310,313,30),0,40)
        t.step('timing',False,(290,310,313,20),.05,40)
        t.step('timing',False,(290,310,313,20),.067,40)
        self.assertEqual(t.velocity,200)
