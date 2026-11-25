import unittest
from timing import TimingLead

class TimingTests(unittest.TestCase):
    def test_approach_right(self):
        t=TimingLead();t.step('timing',False,(250,300,390,50),0,100)
        self.assertTrue(t.step('timing',False,(280,300,390,20),.1,100)[0])
    def test_approach_left(self):
        t=TimingLead();t.step('timing',False,(440,300,390,50),0,100)
        self.assertTrue(t.step('timing',False,(410,300,390,20),.1,100)[0])
    def test_leaving(self):
        t=TimingLead();t.step('timing',True,(345,300,390,0),0,100)
        self.assertFalse(t.step('timing',True,(375,300,390,0),.1,100)[0])
    def test_zone_change(self):
        t=TimingLead();t.step('timing',False,(250,300,390,50),0,100)
        self.assertEqual(t.step('timing',False,(280,470,540,190),.1,100),(False,None))
    def test_reset(self):
        t=TimingLead();t.step('timing',False,(250,300,390,50),0,100)
        t.step('waiting',False,None,.05,100)
        self.assertEqual(t.step('timing',False,(280,300,390,20),.1,100),(False,None))
    def test_disabled(self):
        t=TimingLead();t.step('timing',False,(250,300,390,50),0,0)
        self.assertEqual(t.step('timing',False,(280,300,390,20),.1,0),(False,None))
    def test_stale(self):
        t=TimingLead();t.step('timing',False,(250,300,390,50),0,100)
        self.assertEqual(t.step('timing',False,(280,300,390,20),1,100),(False,None))
    def test_no_lead_cap(self):
        t=TimingLead();t.step('timing',False,(220,370,410,150),0,500)
        hit,pred=t.step('timing',False,(250,370,410,120),.1,500)
        self.assertTrue(hit);self.assertEqual(pred[0],400)
    def test_bounce_boundary(self):
        t=TimingLead();t.step('timing',True,(510,480,550,0),0,100)
        self.assertFalse(t.step('timing',True,(540,480,550,0),.1,100)[0])
if __name__=='__main__':unittest.main()
