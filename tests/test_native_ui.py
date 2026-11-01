import os,time,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt5 import QtWidgets as Q,QtTest
from sts_studio.ui import Window,Trend
app=Q.QApplication.instance() or Q.QApplication([])

class NativeUI(unittest.TestCase):
    def wait(self,predicate,seconds=3):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents();QtTest.QTest.qWait(5)
            if predicate():return
        self.fail('UI timeout')
    def idle(self):self.wait(lambda:self.w.busy is None)
    def setUp(self):
        self.w=Window(True);self.w.show();self.wait(lambda:self.w.service is not None and self.w.busy is None)
    def tearDown(self):
        self.w.monitor.setChecked(False);self.w.test_active=False;self.w.cancel_auto(silent=True);self.idle()
        self.w.commanded.clear();self.w.uncertain.clear();self.w.service.pending.clear() if self.w.service else None
        self.w.close();app.processEvents()
    def select(self):
        self.w.identify();self.wait(lambda:self.w.current==1 and self.w.values[56].text()!='—' and self.w.busy is None)
        self.w.monitor.setChecked(False);self.idle()
    def test_slider_live_off(self):
        self.select();self.w.live.setChecked(False);self.w.service.link.history.clear();self.w.slider.setValue(1234);self.w.slider_release();app.processEvents()
        self.assertFalse(any(p[4] in (3,4,131) for p in self.w.service.link.history))
    def test_plot_bounds(self):
        t=Trend();t.rows.append({'timestamp':10,56:2048});t.bounds=(10,-10)
        self.assertLess(t.ranges()[2],t.ranges()[3]);t.bounds=(-100,100);self.assertEqual(t.ranges()[2:],(-100,100))
    def test_scan_memory_and_control(self):
        self.w.last.setValue(3);self.w.scan();self.idle();self.assertEqual(self.w.servos.topLevelItemCount(),2)
        self.w.tabs.setCurrentIndex(1);self.idle();self.w.servos.topLevelItem(0).setSelected(True);self.wait(lambda:self.w.snapshot is not None and self.w.busy is None)
        self.w.monitor.setChecked(False);self.idle();self.assertEqual(self.w.memory.rowCount(),48)
        self.w.goal.setValue(1234);self.w.speed.setValue(321);self.w.acc.setValue(17);self.w.time_raw.setValue(456);self.w.send();self.idle()
        self.assertEqual(self.w.service.link.mem[1][42:44],b'\xd2\x04')
        self.w.stop_all();self.idle();self.assertFalse(self.w.commanded)
    def test_auto_can_cancel_without_queued_motion(self):
        self.select();self.w.start_value.setValue(1000);self.w.end_value.setValue(1100);self.w.sweep_delay.setValue(20)
        self.w.begin_auto(False);self.wait(lambda:len([p for p in self.w.service.link.history if p[4]==3])>=2)
        self.w.stop_all();self.wait(lambda:not self.w.auto and not self.w.pending_off and self.w.busy is None)
        self.assertEqual(self.w.service.link.mem[1][40],0);self.assertFalse(self.w.commanded)
    def test_readonly_unknown_fw(self):
        self.w.service.link.mem[1][0]=99;self.w.identify();self.wait(lambda:self.w.current==1 and self.w.busy is None)
        self.assertIsNone(self.w.service.servos[1].profile)
        self.assertTrue(all(not b.isEnabled() for b in self.w.device_buttons+self.w.motion_buttons))
    def test_stop_after_one_device_missing_still_stops_other(self):
        self.select();self.w.service.discover(2);self.w.commanded={1,2};self.w.service.link.mem[2][40]=1;self.w.service.link.mem.pop(1)
        self.w.stop_all();self.idle();self.assertEqual(self.w.service.link.mem[2][40],0);self.assertIn('未確認',self.w.health.text())
    def test_test_toggle_and_clear(self):
        self.select();self.w.toggle_test();self.wait(lambda:self.w.stats.success>=2);self.w.toggle_test();self.idle();self.assertFalse(self.w.test_active)
        self.w.clear_test();self.assertEqual(self.w.stats.attempts,0)
    def test_close_while_scan_cancels(self):
        self.w.scan();self.w.close();self.wait(lambda:not self.w.isVisible());self.w.service=None

if __name__=='__main__':unittest.main()
