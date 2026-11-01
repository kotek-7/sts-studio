import os,time,threading,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt5 import QtWidgets as Q,QtTest
from sts_studio.ui import Window
from sts_studio.catalog import identify
from sts_studio.simulator import VirtualLink
from sts_studio.service import Service
from sts_studio.files import Recorder
from tempfile import TemporaryDirectory
from pathlib import Path
app=Q.QApplication.instance() or Q.QApplication([])

class CompatibilityFixes(unittest.TestCase):
    def wait(self,p,timeout=2):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            app.processEvents();QtTest.QTest.qWait(2)
            if p():return
        self.fail('timeout')
    def setUp(self):
        self.w=Window(True);self.w.show();self.wait(lambda:self.w.service is not None and not self.w.busy)
        self.w.identify();self.wait(lambda:self.w.current==1 and self.w.values[56].text()!='—' and not self.w.busy)
    def tearDown(self):
        w=self.w;w.monitor.setChecked(False);w.test_active=False;w.cancel_auto(silent=True);w.pending_manual=None
        self.wait(lambda:not w.busy);w.commanded.clear();w.uncertain.clear();w.service.pending.clear();w.close();app.processEvents()
    def settle(self):self.wait(lambda:not self.w.busy and not self.w.pending_off and not self.w.pending_pwm_off and self.w.pending_mode is None and self.w.pending_manual is None)
    def test_stop_keeps_feedback_and_recording(self):
        w=self.w
        with TemporaryDirectory() as folder:
            rec=Recorder(Path(folder)/'capture.txt',True);w.capture_rows=[];w.capture={'recorder':rec,'interval':30,'flush_at':time.monotonic()+30}
            w.stop_all();self.settle();self.assertTrue(w.monitor.isChecked());n=len(w.capture_rows)
            self.wait(lambda:len(w.capture_rows)>n);self.assertEqual(w.service.link.mem[1][40],0);w.capture_finish()
    def test_goal_is_feedback_word_not_target(self):
        w=self.w;w.monitor.setChecked(False);self.settle();w.service.link.mem[1][67:69]=b'\x01\x80';w.service.link.history.clear()
        result=w.service.feedback(1);w.show_feedback(result)
        self.assertEqual(result['goal'],-1);self.assertEqual(w.values['goal'].text(),'-1')
        self.assertEqual(len(w.service.link.history),1);self.assertEqual(w.service.link.history[0][5:7],b'\x38\x11')
    def test_selection_does_not_read_whole_memory(self):
        w=self.w
        self.assertIsNone(w.snapshot)
        reads=[p for p in w.service.link.history if p[4]==2]
        self.assertFalse(any(p[5:7] in (b'\x00\x28',b'\x28\x1f') for p in reads))
    def test_programming_refresh_preserves_edit(self):
        w=self.w;w.tabs.setCurrentIndex(1);self.wait(lambda:w.snapshot is not None and not w.busy)
        row=next(i for i in range(w.memory.rowCount()) if w.memory.item(i,0).text()=='21');w.memory.item(row,3).setText('55')
        w.service.link.mem[1][21]=44
        self.wait(lambda:w.memory.item(row,2).text()=='44');self.assertEqual(w.memory.item(row,3).text(),'55')
    def test_live_slider_and_stop_discards_waiting_target(self):
        w=self.w;self.assertTrue(w.live.isChecked());w.slider.setValue(1200)
        self.wait(lambda:int.from_bytes(w.service.link.mem[1][42:44],'little')==1200)
        w.submit('待機',lambda cancel:time.sleep(.03));w.slider.setValue(1600);w.stop_all();self.settle()
        self.assertEqual(int.from_bytes(w.service.link.mem[1][42:44],'little'),1200);self.assertIsNone(w.pending_manual)
    def test_step_timer_is_independent(self):
        w=self.w;w.period.setValue(1000);w.monitor.setChecked(False);self.settle();stamps=[]
        w.service.link.trace=lambda direction,p:stamps.append(time.monotonic()) if direction=='TX' and p[4:6]==b'\x03\x29' else None
        w.start_value.setValue(1000);w.end_value.setValue(1100);w.step_delay.setValue(10);w.begin_auto(True)
        self.wait(lambda:len(stamps)>=6);w.cancel_auto(silent=True)
        self.assertLess(stamps[5]-stamps[0],.3)
    def test_tab_mode_switch_and_pwm_stop(self):
        w=self.w;w.tabs.setCurrentIndex(3);self.settle();self.assertEqual(w.service.link.adapter[9],0)
        w.service.pwm('enable',1);w.stop_all();self.settle();self.assertEqual(w.service.link.adapter[35],0);self.assertEqual(w.service.link.adapter[9],0)
        w.tabs.setCurrentIndex(0);self.settle();self.assertEqual(w.service.link.adapter[9],1)
        n=len(w.trend.rows);self.wait(lambda:len(w.trend.rows)>n)
    def test_fast_test_ignores_monitor_period(self):
        w=self.w;w.period.setValue(5000);w.tabs.setCurrentIndex(2);self.settle();w.toggle_test()
        self.wait(lambda:w.stats.success>=20);w.toggle_test();self.settle()
    def test_failed_operation_keeps_monitor(self):
        w=self.w
        def fail(cancel):raise ValueError('test failure')
        self.settle();w.submit('設定保存',fail);self.settle();self.assertTrue(w.monitor.isChecked())
    def test_target_write_does_not_claim_torque_on(self):
        w=self.w;w.send();self.settle();self.assertEqual(w.service.link.mem[1][40],0);self.assertFalse(w.commanded)
    def test_default_baud_and_search_order(self):
        self.assertEqual(self.w.baud.currentText(),'1000000') # demo transport reports its own speed
        plain=Window(False)
        try:self.assertEqual(plain.baud.currentText(),'115200')
        finally:plain.close()
        link=VirtualLink();service=Service(link);service.scan(252,253,threading.Event(),lambda *a:None)
        self.assertEqual([p[2] for p in link.history],[253,252])
    def test_debug_profiles_without_memory_table(self):
        for major,minor,start in [(0,25,56),(0,240,86),(2,10,56),(2,30,56),(20,0,64)]:
            model,p=identify(bytes([major,minor,0,9,3,1,0,0,1]));self.assertIsNotNone(p);self.assertFalse(p.programmable);self.assertEqual(p.feedback_start,start)

    def test_motion_sends_no_extra_read(self):
        w=self.w;w.monitor.setChecked(False);self.settle()
        for method in ['write','sync','registered']:
            w.service.link.history.clear();w.service.control([1],1234,321,17,456,method)
            self.assertEqual(len(w.service.link.history),1)
        w.service.link.history.clear();w.service.action();self.assertEqual(len(w.service.link.history),1)
    def test_step_observed_sequence(self):
        from sts_studio.automation import Pattern
        pattern=Pattern(1000,1100,30,clamp=False)
        self.assertEqual([pattern.next() for _ in range(9)],[1030,1060,1090,1120,1090,1060,1030,1000,1030])
    def test_profile_selection_never_sends_motion(self):
        w=self.w;w.monitor.setChecked(False);self.settle();w.goal.setValue(3000)
        w.service.link.mem[2][0:2]=bytes([0,1]);w.service.discover(2);w.service.link.history.clear()
        w.current=2;w.activate_selection();self.settle()
        self.assertFalse(any(p[4] in (3,4,131) and p[2]!=253 for p in w.service.link.history))
    def test_hardware_status_is_not_packet_status(self):
        w=self.w;w.monitor.setChecked(False);self.settle();w.service.link.mem[1][65]=1
        result=w.service.feedback(1);self.assertEqual(result['values'][65],1);self.assertEqual(result['error'],0)
    def test_monitor_keeps_controls_and_status_stable(self):
        from PyQt5 import QtCore as C
        w=self.w;w.monitor.setChecked(False);self.settle();events=[]
        class Watch(C.QObject):
            def eventFilter(self,obj,event):
                if event.type()==C.QEvent.EnabledChange:events.append(obj)
                return False
        watch=Watch();widgets=[w.connection,w.search,w.servos,w.torque]+w.motion_buttons+w.device_buttons
        for widget in widgets:widget.installEventFilter(watch)
        before=w.state_label.text()
        for _ in range(3):
            w.submit('監視',lambda cancel:(time.sleep(.02),w.service.feedback(1))[1],w.show_feedback,True)
            self.assertEqual(w.state_label.text(),before);self.settle()
        self.assertEqual(events,[])
        for widget in widgets:widget.removeEventFilter(watch)
    def test_unchanged_memory_does_not_emit_cell_changes(self):
        w=self.w;w.monitor.setChecked(False);self.settle();snapshot=w.service.snapshot(1);w.show_memory(snapshot)
        changes=[];w.memory.itemChanged.connect(lambda item:changes.append((item.row(),item.column())))
        w.show_memory(snapshot);self.assertEqual(changes,[])
        updated=dict(snapshot,values=dict(snapshot['values']));updated['values'][21]+=1
        w.show_memory(updated);self.assertEqual(len(changes),1);self.assertEqual(changes[0][1],2)
    def test_user_action_waits_for_monitor_and_stop_discards_it(self):
        w=self.w;w.monitor.setChecked(False);self.settle();w.service.link.history.clear()
        w.submit('監視',lambda cancel:(time.sleep(.03),w.service.feedback(1))[1],w.show_feedback,True)
        w.torque_change(True);self.assertEqual(len(w.pending_ui),1)
        self.wait(lambda:not w.pending_ui and not w.busy);self.assertEqual(w.service.link.mem[1][40],1)
        w.submit('監視',lambda cancel:(time.sleep(.03),w.service.feedback(1))[1],w.show_feedback,True)
        w.torque_change(True);w.stop_all();self.assertFalse(w.pending_ui);self.settle()
        self.assertEqual(w.service.link.mem[1][40],0)
    def test_open_close_via_actual_button_click(self):
        import sys
        errors=[];previous=sys.excepthook;sys.excepthook=lambda kind,value,tb:errors.append(str(value))
        w=Window(False);w.demo.setChecked(True)
        try:
            w.connection.click();self.assertEqual(errors,[])
            self.wait(lambda:w.service is not None and not w.busy)
            w.identify_button.click();self.assertEqual(errors,[])
            self.wait(lambda:w.current==1 and not w.busy)
            w.monitor.setChecked(False)
            w.connection.click();self.assertEqual(errors,[])
            self.wait(lambda:w.service is None)
        finally:
            w.close();sys.excepthook=previous
    def test_decorated_qt_buttons_discard_only_unused_argument(self):
        from sts_studio.ui import after_monitor
        class Receiver:
            busy=None
            def __init__(self):self.pending_ui=[];self.calls=[]
            @after_monitor
            def no_argument(self):self.calls.append('clicked')
            @after_monitor
            def boolean_argument(self,checked):self.calls.append(checked)
        receiver=Receiver();button=Q.QPushButton();button.setCheckable(True)
        button.clicked.connect(receiver.no_argument);button.clicked.connect(receiver.boolean_argument)
        button.click();self.assertEqual(receiver.calls,['clicked',True])
        receiver.busy='監視';button.click();self.assertEqual(len(receiver.pending_ui),2)
        receiver.busy=None
        for callback in receiver.pending_ui:callback()
        self.assertEqual(receiver.calls,['clicked',True,'clicked',False])
