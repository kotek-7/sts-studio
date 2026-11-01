"""Qt interface for servo control, configuration, diagnostics, and PWM."""
import csv,json,math,time
from collections import deque
from functools import wraps
from inspect import signature
from pathlib import Path
from PyQt5 import QtCore as C,QtGui as G,QtWidgets as Q
from serial.tools import list_ports
from .catalog import ROOT,PROTOCOL
from .wire import SerialLink,Timeout,StatusError
from .simulator import VirtualLink
from .service import Service
from .automation import Pattern,CommunicationStats
from .files import ParameterImage,Recorder,write_csv,inspect_firmware
from .jobs import Worker

SERIES={56:('Position','#172b4d'), 'goal':('Goal','#2563eb'),60:('Torque','#dc2626'),58:('Speed','#16803d'),69:('Current','#0891b2'),63:('Temperature','#b45309'),62:('Voltage','#7c3aed')}

def after_monitor(fn):
    """Run UI actions after an in-flight feedback read, on the GUI thread."""
    positional_count=len(signature(fn).parameters)-1
    @wraps(fn)
    def wrapped(self,*args,**kwargs):
        # Qt clicked(bool) supplies an extra argument to variadic wrappers.
        args=args[:positional_count]
        if self.busy=='監視':
            self.pending_ui.append(lambda:wrapped(self,*args,**kwargs))
            return
        return fn(self,*args,**kwargs)
    return wrapped

class Trend(Q.QWidget):
    def __init__(self):
        super().__init__();self.setMinimumSize(380,210);self.rows=deque(maxlen=100000)
        self.visible={56,60,58};self.window=30;self.offset=0;self.bounds=None;self.position_max=4096;self.speed_multiplier=.2
    def ranges(self):
        if not self.rows:return 0,1,0,4095
        end=self.rows[-1]['timestamp']-self.offset;start=end-self.window
        if self.bounds is not None and all(math.isfinite(x) for x in self.bounds) and self.bounds[0]<self.bounds[1]:lo,hi=self.bounds
        else:lo,hi=0,self.position_max
        return start,end,lo,hi
    def paintEvent(self,event):
        p=G.QPainter(self);p.setRenderHint(G.QPainter.Antialiasing);p.fillRect(self.rect(),G.QColor('white'))
        rect=C.QRectF(57,10,max(1,self.width()-115),max(1,self.height()-37));start,end,lo,hi=self.ranges()
        for i in range(6):
            y=rect.top()+rect.height()*i/5;p.setPen(G.QColor('#d7dce5'));p.drawLine(C.QPointF(rect.left(),y),C.QPointF(rect.right(),y))
            p.setPen(G.QColor('#5c6472'));p.drawText(C.QRectF(0,y-10,52,20),C.Qt.AlignRight|C.Qt.AlignVCenter,f'{hi-(hi-lo)*i/5:.0f}')
            p.drawText(C.QRectF(rect.right()+4,y-10,50,20),C.Qt.AlignLeft|C.Qt.AlignVCenter,f'{1000-2000*i/5:.0f}')
        if not self.rows:p.drawText(rect,C.Qt.AlignCenter,'サーボを選択してモニターを開始');return
        p.save();p.setClipRect(rect)
        for key in self.visible:
            path=G.QPainterPath();first=True
            for r in self.rows:
                t=r['timestamp']
                if not start<=t<=end or r.get(key) is None:continue
                value=r[key]*(self.speed_multiplier if key==58 else 1)
                bottom,top=(lo,hi) if key in (56,'goal') else (-1000,1000)
                x=rect.left()+(t-start)/(end-start)*rect.width();y=rect.bottom()-(value-bottom)/(top-bottom)*rect.height()
                if first:path.moveTo(x,y);first=False
                else:path.lineTo(x,y)
            p.setPen(G.QPen(G.QColor(SERIES[key][1]),1.6));p.drawPath(path)
        p.restore();p.setPen(G.QColor('#5c6472'));p.drawText(C.QRectF(rect.left(),rect.bottom()+5,rect.width(),20),C.Qt.AlignRight,f'横軸 {self.window:g}秒 / 過去 {self.offset:g}秒 / 左軸:位置 / 右軸:その他')

class Window(Q.QMainWindow):
    def __init__(self,demo=False):
        super().__init__();self.setWindowTitle('STS Studio');self.resize(1240,900)
        self.worker=Worker();self.worker.done.connect(self.job_done);self.worker.failed.connect(self.job_failed);self.worker.progress.connect(self.scan_progress);self.worker.trace.connect(self.trace)
        self.service=None;self.busy=None;self.job_counter=0;self.callbacks={};self.current=None;self.snapshot=None
        self.auto=None;self.test_active=False;self.stats=CommunicationStats();self.failures=0;self.after_idle=None;self.closing=False
        self.pending_ui=deque();self.pending_mode=None;self.adapter_mode=1;self.pending_pwm_off=False;self.pending_manual=None;self.next_poll=0;self.next_test=0;self.pending_off=[];self.uncertain=set();self.commanded=set();self.capture=None;self.capture_rows=[];self.motion_buttons=[];self.device_buttons=[]
        main=Q.QWidget();self.setCentralWidget(main);outer=Q.QVBoxLayout(main);outer.setContentsMargins(14,12,14,8)
        title=Q.QHBoxLayout();label=Q.QLabel('STS Studio');label.setStyleSheet('font-size:22px;font-weight:700;color:#163453');title.addWidget(label);title.addWidget(Q.QLabel('サーボ設定・モニター'));title.addStretch();self.state_label=Q.QLabel('DISCONNECTED');title.addWidget(self.state_label);outer.addLayout(title)
        split=Q.QSplitter();outer.addWidget(split,1);sidebar=Q.QWidget();side=Q.QVBoxLayout(sidebar);side.setContentsMargins(0,0,8,0)
        group=Q.QGroupBox('Com Settings / 接続');form=Q.QFormLayout(group)
        self.port=Q.QComboBox();self.port.setMinimumWidth(190);self.refresh=Q.QPushButton('更新');self.refresh.clicked.connect(self.ports)
        portrow=Q.QWidget();pr=Q.QHBoxLayout(portrow);pr.setContentsMargins(0,0,0,0);pr.addWidget(self.port,1);pr.addWidget(self.refresh)
        self.baud=Q.QComboBox();self.baud.addItems([str(v) for v in PROTOCOL['port']['baud_choices']]);self.baud.setCurrentText('115200');self.parity=Q.QComboBox();self.parity.addItems(['N','O','E']);self.timeout=self.spin(5,5000,50)
        self.demo=Q.QCheckBox('デモ（実機通信なし）');self.demo.setChecked(demo)
        self.connection=Q.QPushButton('Open / 接続');self.connection.clicked.connect(self.toggle_connection)
        for name,w in [('Port',portrow),('Baud',self.baud),('Parity',self.parity),('Timeout ms',self.timeout),('',self.demo),('',self.connection)]:form.addRow(name,w)
        side.addWidget(group)
        group=Q.QGroupBox('Servo List / サーボ');lv=Q.QVBoxLayout(group);bounds=Q.QHBoxLayout();self.first=self.spin(0,253,0);self.last=self.spin(0,253,253);bounds.addWidget(self.first);bounds.addWidget(Q.QLabel('〜'));bounds.addWidget(self.last);lv.addLayout(bounds)
        self.search=Q.QPushButton('Search / 検索');self.search.clicked.connect(self.scan);lv.addWidget(self.search)
        self.scan_status=Q.QLabel('未検索');lv.addWidget(self.scan_status)
        self.servos=Q.QTreeWidget();self.servos.setHeaderLabels(['ID','Model','FW']);self.servos.setSelectionMode(Q.QAbstractItemView.ExtendedSelection);self.servos.setColumnWidth(0,40);self.servos.setColumnWidth(1,120);self.servos.itemSelectionChanged.connect(self.selection_changed);lv.addWidget(self.servos,1)
        lv.addWidget(Q.QLabel('Ctrl / Shiftで複数台を選択'))
        direct=Q.QHBoxLayout();self.direct_id=self.spin(0,253,1);self.identify_button=Q.QPushButton('ID指定');self.identify_button.clicked.connect(self.identify);direct.addWidget(self.direct_id);direct.addWidget(self.identify_button);lv.addLayout(direct);side.addWidget(group,1)
        self.off=Q.QPushButton('STOP / トルク・PWM OFF');self.off.setStyleSheet('background:#a32020;color:white;font-weight:bold;padding:10px');self.off.clicked.connect(self.stop_all);side.addWidget(self.off)
        split.addWidget(sidebar);self.tabs=Q.QTabWidget();split.addWidget(self.tabs);split.setSizes([290,940])
        self.build_debug();self.build_programming();self.build_upgrade();self.build_pwm();self.build_log()
        self.timer=C.QTimer(self);self.timer.setTimerType(C.Qt.PreciseTimer);self.timer.setInterval(2);self.timer.timeout.connect(self.tick);self.timer.start();self.tabs.currentChanged.connect(self.tab_changed)
        self.ports();self.update_controls();self.note('ポートを開いて検索してください。接続だけではサーボ指令を送りません。')
        if demo:C.QTimer.singleShot(0,self.toggle_connection)
    @staticmethod
    def spin(lo,hi,value):
        s=Q.QSpinBox();s.setRange(lo,hi);s.setValue(value);return s
    def button(self,text,fn,kind='device'):
        b=Q.QPushButton(text);b.clicked.connect(fn)
        if kind=='device':self.device_buttons.append(b)
        elif kind=='motion':self.motion_buttons.append(b)
        return b
    def tab(self,title):
        content=Q.QWidget();layout=Q.QVBoxLayout(content);layout.setSpacing(9);scroll=Q.QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(Q.QFrame.NoFrame);scroll.setWidget(content);self.tabs.addTab(scroll,title);return layout
    def build_debug(self):
        lay=self.tab('Debug / 操作');top=Q.QHBoxLayout();self.trend=Trend();top.addWidget(self.trend,1);controls=Q.QGridLayout()
        for index,(key,(name,color)) in enumerate(SERIES.items()):
            c=Q.QCheckBox(name);c.setChecked(key in self.trend.visible);c.setStyleSheet('color:'+color);c.toggled.connect(lambda checked,k=key:self.series_toggle(k,checked));controls.addWidget(c,index//2,index%2)
        self.window_s=self.spin(1,600,30);self.offset_s=self.spin(0,600,0);self.lower=Q.QDoubleSpinBox();self.upper=Q.QDoubleSpinBox()
        for w in [self.lower,self.upper]:w.setRange(-1e9,1e9);w.valueChanged.connect(self.plot_config)
        self.window_s.valueChanged.connect(self.plot_config);self.offset_s.valueChanged.connect(self.plot_config)
        for index,(name,w) in enumerate([('表示幅 秒',self.window_s),('過去へ 秒',self.offset_s),('Low',self.lower),('Up（0=auto）',self.upper)]):controls.addWidget(Q.QLabel(name),4+index,0);controls.addWidget(w,4+index,1)
        top.addLayout(controls);lay.addLayout(top,1)
        middle=Q.QHBoxLayout();control=Q.QGroupBox('Servo Control');cl=Q.QGridLayout(control);self.method=Q.QComboBox();self.method.addItem('Write','write');self.method.addItem('Sync Write','sync');self.method.addItem('Reg Write','registered');cl.addWidget(self.method,0,0,1,2)
        self.torque=Q.QCheckBox('Torque Enable');self.torque.clicked.connect(self.torque_change);cl.addWidget(self.torque,0,2,1,2)
        self.slider=Q.QSlider(C.Qt.Horizontal);self.slider.setRange(0,4095);self.slider.setValue(2047);self.slider.valueChanged.connect(self.slider_changed);cl.addWidget(self.slider,1,0,1,4)
        self.acc=self.spin(0,254,0);self.goal=self.spin(-32766,32766,2047);self.speed=self.spin(-32766,32766,0);self.time_raw=self.spin(0,65535,0)
        self.goal.valueChanged.connect(self.goal_changed)
        for row,name,w,col in [(2,'Acc',self.acc,0),(2,'Goal',self.goal,2),(3,'Speed',self.speed,0),(3,'Time (raw)',self.time_raw,2)]:cl.addWidget(Q.QLabel(name),row,col);cl.addWidget(w,row,col+1)
        self.live=Q.QCheckBox('Live（スライダー操作で送信）');self.live.setChecked(True);cl.addWidget(self.live,4,0,1,4)
        cl.addWidget(self.button('Set / 送信',self.send,'motion'),5,0,1,2);cl.addWidget(self.button('Action',self.action,'motion'),5,2,1,2);middle.addWidget(control,1)
        feedback=Q.QGroupBox('Servo Feedback');fl=Q.QGridLayout(feedback);self.values={}
        for i,(key,name) in enumerate([(62,'Voltage [V]'),(60,'Torque [raw]'),(69,'Current [raw]'),(58,'Speed [step/s]'),(63,'Temperature [°C]'),(56,'Position [step]'),(66,'Moving'),('goal','Goal')]):
            value=Q.QLabel('—');value.setStyleSheet('font-size:15px;font-weight:600');fl.addWidget(Q.QLabel(name),i//2,(i%2)*2);fl.addWidget(value,i//2,(i%2)*2+1);self.values[key]=value
        self.health=Q.QLabel('未読取');self.health.setWordWrap(True);fl.addWidget(self.health,4,0,1,4)
        self.monitor=Q.QCheckBox('モニター');self.period=self.spin(20,5000,50);fl.addWidget(self.monitor,5,0,1,2);fl.addWidget(self.period,5,2,1,2);middle.addWidget(feedback,1);lay.addLayout(middle)
        bottom=Q.QHBoxLayout();auto=Q.QGroupBox('Auto debug');al=Q.QGridLayout(auto);self.start_value=self.spin(-32766,32766,0);self.end_value=self.spin(-32766,32766,4095);self.sweep_delay=self.spin(10,600000,2500);self.step_size=self.spin(1,32766,4);self.step_delay=self.spin(10,600000,20);self.step_size.setToolTip('Stepは端点を跨いだ指令を送信してから折り返します')
        for row,name,w,col in [(0,'Start',self.start_value,0),(1,'End',self.end_value,0),(0,'Sweep ms',self.sweep_delay,2),(1,'Step',self.step_size,2),(2,'Step ms',self.step_delay,2)]:al.addWidget(Q.QLabel(name),row,col);al.addWidget(w,row,col+1)
        al.addWidget(self.button('Sweep',lambda:self.begin_auto(False),'motion'),0,4);al.addWidget(self.button('Step',lambda:self.begin_auto(True),'motion'),1,4);stop=Q.QPushButton('自動動作中止');stop.clicked.connect(self.cancel_auto);al.addWidget(stop,2,4);bottom.addWidget(auto,3)
        data=Q.QGroupBox('Data analysis');dl=Q.QFormLayout(data);self.capture_seconds=self.spin(1,86400,30);dl.addRow('保存間隔 [s]',self.capture_seconds);self.capture_count=Q.QLabel('0 rows');dl.addRow(self.capture_count)
        dr=Q.QHBoxLayout();self.export_button=Q.QPushButton('Export / 記録');self.export_button.clicked.connect(self.capture_toggle);dr.addWidget(self.export_button);empty=Q.QPushButton('Empty');empty.clicked.connect(self.clear_data);dr.addWidget(empty);dl.addRow(dr);save=Q.QPushButton('現在の記録を保存');save.clicked.connect(self.save_capture);dl.addRow(save);bottom.addWidget(data,2);lay.addLayout(bottom)
    def build_programming(self):
        lay=self.tab('Programming / 設定');row=Q.QHBoxLayout()
        for text,fn in [('Read / 再読込',self.read_memory),('Save .xdat',self.save_image),('Load .xdat',self.load_image),('Recovery',self.recovery),('中点校正',self.calibrate)]:row.addWidget(self.button(text,fn))
        lay.addLayout(row)
        self.memory=Q.QTableWidget(0,7);self.memory.setHorizontalHeaderLabels(['Addr','Memory','Value','Edit','Area','R/W','Range']);self.memory.setSelectionBehavior(Q.QAbstractItemView.SelectRows);self.memory.setSelectionMode(Q.QAbstractItemView.SingleSelection);self.memory.itemSelectionChanged.connect(self.describe_register);self.memory.horizontalHeader().setSectionResizeMode(1,Q.QHeaderView.Stretch)
        for i,width in [(0,48),(2,80),(3,80),(4,70),(5,45),(6,125)]:self.memory.setColumnWidth(i,width)
        lay.addWidget(self.memory,1);self.parameter_description=Q.QLabel('項目を選択すると範囲と格納形式を表示します');self.parameter_description.setWordWrap(True);lay.addWidget(self.parameter_description);lay.addWidget(self.button('選択した行の編集値を保存',self.save_parameter))
        label=Q.QLabel('EEPROMの保存にはトルクOFFが必要です。変更後の値は読み戻して確認します。');label.setWordWrap(True);lay.addWidget(label)
    def build_upgrade(self):
        lay=self.tab('診断・ファイル検査');group=Q.QGroupBox('Communication test');gl=Q.QVBoxLayout(group);self.test_output=Q.QPlainTextEdit();self.test_output.setReadOnly(True);self.test_output.setMaximumBlockCount(500);gl.addWidget(self.test_output)
        row=Q.QHBoxLayout();self.test_button=Q.QPushButton('Test / 開始');self.test_button.clicked.connect(self.toggle_test);row.addWidget(self.test_button);clear=Q.QPushButton('Clear');clear.clicked.connect(self.clear_test);row.addWidget(clear);gl.addLayout(row);lay.addWidget(group,1)
        group=Q.QGroupBox('Firmware update');fl=Q.QVBoxLayout(group);self.firmware_output=Q.QPlainTextEdit();self.firmware_output.setReadOnly(True);self.firmware_output.setPlainText('ファームウェアの検査に対応しています。\nファームウェアの書き込みには対応していません。');fl.addWidget(self.firmware_output)
        row=Q.QHBoxLayout();openfile=Q.QPushButton('Open / ファイル検査');openfile.clicked.connect(self.open_firmware);row.addWidget(openfile);fl.addLayout(row);lay.addWidget(group,1)
    def build_pwm(self):
        lay=self.tab('PWM / アダプター');label=Q.QLabel('対応アダプターのID253を操作します。サーボへのPWMモード設定とは別機能です。\n実機でのPWM出力は未検証です。');label.setWordWrap(True);lay.addWidget(label)
        row=Q.QHBoxLayout();self.pwm_mode=Q.QPushButton('PWMモードへ');self.pwm_mode.clicked.connect(lambda:self.pwm_command('mode',0));row.addWidget(self.pwm_mode);self.bus_mode=Q.QPushButton('バスモードへ戻す');self.bus_mode.clicked.connect(lambda:self.pwm_command('mode',1));row.addWidget(self.bus_mode);lay.addLayout(row)
        self.pwm_slider=Q.QSlider(C.Qt.Horizontal);self.pwm_slider.setRange(500,2500);self.pwm_slider.setValue(1500);self.pwm_slider.valueChanged.connect(self.pwm_slide);lay.addWidget(self.pwm_slider);self.pulse=self.spin(500,2500,1500);form=Q.QFormLayout();form.addRow('Pulse [µs]',self.pulse);lay.addLayout(form)
        row=Q.QHBoxLayout();self.pwm_buttons=[]
        for value in [500,900,1200,1500,1800,2100,2500]:
            b=Q.QPushButton(str(value));b.clicked.connect(lambda _,v=value:self.pwm_command('pulse',v));row.addWidget(b);self.pwm_buttons.append(b)
        lay.addLayout(row);row=Q.QHBoxLayout()
        for label,fn in [('Pulse送信',lambda:self.pwm_command('pulse',self.pulse.value())),('出力ON',lambda:self.pwm_command('enable',1)),('出力OFF',lambda:self.pwm_command('enable',0))]:
            b=Q.QPushButton(label);b.clicked.connect(fn);row.addWidget(b);self.pwm_buttons.append(b)
        lay.addLayout(row);group=Q.QGroupBox('自動動作 / パルス範囲');form=Q.QFormLayout(group);self.pwm_min=self.spin(500,2500,500);self.pwm_max=self.spin(500,2500,2500);self.pwm_delay=self.spin(10,600000,1000);self.pwm_step=self.spin(1,2000,4)
        for label,w in [('Min µs',self.pwm_min),('Max µs',self.pwm_max),('Delay ms',self.pwm_delay),('Step µs',self.pwm_step)]:form.addRow(label,w)
        row=Q.QHBoxLayout()
        for label,fn in [('Sweep',lambda:self.begin_pwm_auto(False)),('Step',lambda:self.begin_pwm_auto(True)),('中止',self.cancel_auto)]:
            b=Q.QPushButton(label);b.clicked.connect(fn);row.addWidget(b);self.pwm_buttons.append(b)
        form.addRow(row);lay.addWidget(group);lay.addStretch()
    def build_log(self):
        lay=self.tab('通信ログ');self.packet_logging=Q.QCheckBox('HEXパケットをログに含める');lay.addWidget(self.packet_logging);self.log=Q.QPlainTextEdit();self.log.setReadOnly(True);self.log.setMaximumBlockCount(3000);lay.addWidget(self.log)
        row=Q.QHBoxLayout();spec=Q.QPushButton('仕様書を開く');spec.clicked.connect(lambda:G.QDesktopServices.openUrl(C.QUrl.fromLocalFile(str(ROOT/'docs/SPECIFICATION.md'))));row.addWidget(spec);matrix=Q.QPushButton('機能一覧を開く');matrix.clicked.connect(lambda:G.QDesktopServices.openUrl(C.QUrl.fromLocalFile(str(ROOT/'docs/FEATURE_MATRIX.md'))));row.addWidget(matrix);lay.addLayout(row)
    def note(self,text):
        self.statusBar().showMessage(text)
        if hasattr(self,'log'):self.log.appendPlainText(time.strftime('%H:%M:%S')+' '+text)
    def notice(self,text):Q.QMessageBox.information(self,'STS Studio',text)
    def trace(self,kind,raw):
        if self.packet_logging.isChecked():self.log.appendPlainText(kind+' '+raw.hex(' ').upper())
    def ids(self):return sorted(int(i.text(0)) for i in self.servos.selectedItems())
    def update_controls(self):
        connected=self.service is not None;idle=self.busy is None or self.busy=='監視';ready=connected and self.current is not None and bool(self.service.servos.get(self.current)) and self.service.servos[self.current].profile is not None
        for w in [self.port,self.refresh,self.baud,self.parity,self.timeout,self.demo]:w.setEnabled(not connected and idle)
        self.connection.setEnabled(idle and not self.auto);self.connection.setText('Close / 切断' if connected else 'Open / 接続')
        self.search.setEnabled(connected and (idle or self.busy=='検索') and not self.auto);self.search.setText('Stop / 検索中止' if self.busy=='検索' else 'Search / 検索')
        for w in [self.servos,self.identify_button,self.direct_id,self.first,self.last]:w.setEnabled(connected and idle and not self.auto)
        for w in self.motion_buttons:w.setEnabled(ready and idle and not self.auto and not self.test_active and self.service.get(self.current).profile.motion_supported if ready else False)
        for w in self.device_buttons:w.setEnabled(ready and idle and not self.auto and not self.test_active and self.service.get(self.current).profile.programmable if ready else False)
        self.torque.setEnabled(ready and idle and not self.auto and bool(self.service.get(self.current).profile.data['torque_address']) if ready else False);self.off.setEnabled(connected);self.monitor.setEnabled(ready)
        self.export_button.setEnabled(ready or self.capture is not None);self.test_button.setEnabled(ready and not self.auto and (idle or self.test_active))
        for w in [self.pwm_mode,self.bus_mode]+self.pwm_buttons:w.setEnabled(connected and idle and not self.auto)
        state='DISCONNECTED' if not connected else ('AUTO' if self.auto else 'TESTING' if self.test_active else 'BUSY' if not idle else 'READY' if ready else 'CONNECTED')
        self.state_label.setText(('DEMO / ' if self.demo.isChecked() else '')+state)
    def submit(self,name,fn,done=None,quiet=False):
        if self.busy is not None:return False
        self.job_counter+=1;token=self.job_counter;self.busy=name;self.callbacks[token]=(name,done,quiet);self.update_controls();self.worker.submit(token,fn);return True
    def job_done(self,token,result):
        name,callback,quiet=self.callbacks.pop(token);self.busy=None
        try:
            if callback:callback(result)
            if not quiet:self.note(name+' 完了')
        except Exception as e:self.note('画面更新エラー: '+str(e))
        self.finish_job()
    def job_failed(self,token,error):
        name,_,quiet=self.callbacks.pop(token);self.busy=None;self.note(name+': '+str(error))
        if name=='監視':
            self.failures+=1
            self.health.setText('通信途絶 / 表示値は過去の値（再試行中）')
        else:self.next_poll=time.monotonic()+self.period.value()/1000
        self.cancel_auto(silent=True)
        if name=='通信試験':
            self.test_active=False;self.stats.add(0,0,'error');self.test_button.setText('Test / 開始')
        if name=='モード切替':self.adapter_mode=None;self.note('モード切替失敗。再度タブを選択してください')
        if name=='トルクOFF':self.health.setText('トルクOFF未確認 — 接続・電源を確認');self.uncertain.update(self.off_attempt)
        self.finish_job()
    def finish_job(self):
        if self.service:self.baud.setCurrentText(str(self.service.link.baud))
        self.update_controls()
        if self.closing:self.close()
        else:C.QTimer.singleShot(0,self.tick)
    def ports(self):
        previous=self.port.currentData();self.port.clear()
        for p in sorted(list_ports.comports(),key=lambda x:x.device):self.port.addItem(f'{p.device} · {p.description}',p.device)
        idx=self.port.findData(previous)
        if idx>=0:self.port.setCurrentIndex(idx)
    @after_monitor
    def toggle_connection(self):
        if self.service:
            if self.commanded or self.uncertain or self.service.pending:
                self.notice('切断前にSTOPでトルクOFFを確認してください。登録済み指令は外部Actionで実行される可能性があります。');return
            self.monitor.setChecked(False);self.test_active=False;self.capture_finish();self.pending_manual=None;self.pending_mode=None;self.pending_pwm_off=False;self.service.link.close();self.service=None;self.current=None;self.snapshot=None;self.servos.clear();self.update_controls();return
        path=self.port.currentData();demo=self.demo.isChecked();baud=int(self.baud.currentText());parity=self.parity.currentText();timeout=self.timeout.value()
        if not demo and not path:self.note('USBシリアルがありません。更新またはデモを選んでください');return
        def opened(link):
            self.service=Service(link);self.adapter_mode=1;self.pending_mode=0 if self.tabs.currentIndex()==3 else None;self.note('接続しました。検索してください。')
        self.submit('接続',lambda cancel:VirtualLink(self.worker.trace.emit) if demo else SerialLink(path,baud,parity,timeout,self.worker.trace.emit),opened)
    @after_monitor
    def scan(self):
        if self.busy=='検索':self.worker.cancel.set();return
        if self.commanded or self.uncertain:self.notice('検索前にSTOPでトルクOFFを確認してください');return
        first,last=self.first.value(),self.last.value()
        if first>last:self.note('開始IDは終了ID以下にしてください');return
        self.monitor.setChecked(False);self.current=None;self.snapshot=None;self.servos.clear();self.service.servos.clear()
        self.submit('検索',lambda cancel:self.service.scan(first,last,cancel,lambda sid,s:self.worker.progress.emit((sid,s))),lambda found:self.scan_status.setText(f'{len(found)} 台検出'))
    def add_servo(self,s):
        existing=next((self.servos.topLevelItem(i) for i in range(self.servos.topLevelItemCount()) if int(self.servos.topLevelItem(i).text(0))==s.sid),None)
        if not existing:existing=Q.QTreeWidgetItem(self.servos)
        existing.setText(0,str(s.sid));existing.setText(1,s.model);existing.setText(2,s.firmware)
        if s.profile is None:existing.setToolTip(1,'未対応ファームウェア: 書き込み禁止')
        return existing
    def scan_progress(self,payload):
        sid,servo=payload;self.scan_status.setText(f'ID {sid} を確認')
        if servo:self.add_servo(servo)
    @after_monitor
    def identify(self):
        sid=self.direct_id.value();self.pending_manual=None
        def selected(result):
            s,b=result;self.servos.blockSignals(True);self.servos.clearSelection();item=self.add_servo(s);item.setSelected(True);self.servos.setCurrentItem(item);self.servos.blockSignals(False);self.current=s.sid;C.QTimer.singleShot(0,self.activate_selection)
        self.submit('ID識別',lambda cancel:self.service.discover(sid),selected)
    @after_monitor
    def selection_changed(self):
        if self.busy:return
        ids=self.ids();self.current=ids[0] if ids else None;self.pending_manual=None;self.snapshot=None;self.monitor.setChecked(False);self.trend.rows.clear();self.trend.update();self.memory.setRowCount(0)
        if self.current is not None and self.service.servos[self.current].profile:self.activate_selection()
        self.update_controls()
    @after_monitor
    def read_memory(self):
        if self.current is not None:self.submit('メモリ読取',lambda cancel:self.service.snapshot(self.current),self.show_memory)
    def activate_selection(self):
        if self.current is None:return
        p=self.service.servos[self.current].profile
        if not p:return
        self.slider.blockSignals(True);self.slider.setRange(0,4095 if p.family!='SCS' else 1023);self.slider.blockSignals(False)
        self.end_value.setValue(self.slider.maximum())
        self.monitor.setChecked(True);self.next_poll=0;self.trend.position_max=4096/p.position_divisor;self.trend.speed_multiplier=p.speed_multiplier
        if self.tabs.currentIndex()==1 and p.programmable:self.read_memory()
        else:self.submit('監視',lambda cancel:self.service.feedback(self.current),self.show_feedback,True)
    def describe_register(self):
        i=self.memory.currentRow()
        if i<0 or self.current is None:return
        r=self.service.get(self.current).profile.field(int(self.memory.item(i,0).text()))
        self.parameter_description.setText(f'{r.name} / address {r.address} / {r.size} byte / {r.area} / {r.access} / 範囲 {r.limits[0]}..{r.limits[1]} / 符号bit {r.sign_bit}')
    def show_memory(self,result):
        self.snapshot=result;sid=result['id'];p=self.service.get(sid).profile;rows=p.registers
        rebuild=self.memory.rowCount()!=len(rows) or self.memory.property('profile')!=p.name
        if rebuild:self.memory.setRowCount(len(rows));self.memory.setProperty('profile',p.name)
        for i,r in enumerate(rows):
            lo,hi=r.limits
            texts=[str(r.address),r.name,str(result['values'].get(r.address,'—')),'',r.area,r.access,f'{lo}..{hi}' if r.writable else 'read only']
            for j,text in enumerate(texts):
                if j==3 and not rebuild and self.memory.item(i,j) is not None:continue
                item=self.memory.item(i,j)
                if item is None:
                    item=Q.QTableWidgetItem();self.memory.setItem(i,j,item)
                if item.text()!=text:item.setText(text)
                if rebuild:
                    item.setData(C.Qt.UserRole,r.address)
                    if j!=3 or not r.writable:item.setFlags(item.flags()&~C.Qt.ItemIsEditable)
        self.torque.blockSignals(True);self.torque.setChecked(bool(result['values'].get(40,0)));self.torque.blockSignals(False)
        if result['values'].get(40)==0:self.commanded.discard(sid)
        self.show_feedback(dict(id=sid,values=result['values'],error=result['error'],timestamp=time.time(),goal=result.get('goal')))
    def show_feedback(self,result):
        self.failures=0;row={**result['values'],'id':result['id'],'timestamp':result['timestamp'],'error':result['error'],'goal':result.get('goal')}
        for key,label in self.values.items():
            v=row.get(key);label.setText('—' if v is None else f'{v/10:.1f}' if key==62 else str(v))
        self.health.setText(('トルクOFF未確認 / ' if row['id'] in self.uncertain else '')+('Normal' if not row['error'] else str(StatusError(row['error'])))+f' / ID {row["id"]} / '+time.strftime('%H:%M:%S'))
        self.trend.rows.append(row);self.trend.update()
        if self.capture:
            self.capture_rows.append(row);self.capture['recorder'].append(row);self.capture_count.setText(f'{len(self.capture_rows)} rows')
            if len(self.capture_rows)>=100000:self.capture_finish()
    def tab_changed(self,index):
        self.cancel_auto(silent=True);self.test_active=False;self.test_button.setText('Test / 開始');self.pending_manual=None
        if self.service:self.pending_mode=0 if index==3 else 1
        self.next_poll=0;self.update_controls()
    def tick(self):
        now=time.monotonic()
        if self.capture and now>=self.capture['flush_at']:
            try:self.capture['recorder'].flush();self.capture['flush_at']=now+self.capture['interval']
            except Exception as e:self.note('記録保存失敗（データ保持）: '+str(e));self.capture=None;self.export_button.setText('Export / 記録')
        if self.busy or not self.service or self.closing:return
        if self.pending_pwm_off:
            self.pending_pwm_off=False;self.submit('PWM出力OFF',lambda cancel:self.service.pwm('enable',0),self.note);return
        if self.pending_mode is not None:
            mode=self.pending_mode;self.pending_mode=None
            def switched(_):self.adapter_mode=mode;self.next_poll=0
            self.submit('モード切替',lambda cancel:self.service.pwm('mode',mode),switched);return
        if self.pending_off:
            if self.adapter_mode==0:self.pending_mode=1;return
            ids=self.pending_off;self.pending_off=[];self.torque_off(ids);return
        if self.pending_ui:
            self.pending_ui.popleft()();return
        if self.adapter_mode is None:return
        if self.pending_manual is not None:
            kind,args=self.pending_manual;self.pending_manual=None
            if kind=='servo':self.dispatch_control(args)
            else:self.submit('PWM送信',lambda cancel:self.service.pwm('pulse',args),self.note)
            return
        if self.auto and now>=self.auto['next']:self.auto_tick();return
        if self.test_active and now>=self.next_test:self.test_tick();return
        if self.adapter_mode!=1 or self.tabs.currentIndex() not in (0,1):return
        if self.monitor.isChecked() and self.current is not None and now>=self.next_poll:
            self.next_poll=now+self.period.value()/1000
            if self.tabs.currentIndex()==1 and self.service.get(self.current).profile.programmable:self.submit('監視',lambda cancel:self.service.snapshot(self.current),self.show_memory,True)
            else:self.submit('監視',lambda cancel:self.service.feedback(self.current),self.show_feedback,True)
    def goal_changed(self,value):
        self.slider.blockSignals(True);self.slider.setValue(max(0,min(4095,value)));self.slider.blockSignals(False)
    def slider_changed(self,value):
        self.goal.setValue(value)
        if self.live.isChecked() and self.current is not None and not self.auto:self.send()
    def slider_release(self):
        pass  # Value changes already submit the latest target.
    def pwm_slide(self,value):
        self.pulse.setValue(value)
        if self.service and not self.auto:
            self.pending_manual=('pwm',value);self.tick()
    def send(self):
        ids=self.ids()
        if not ids or not self.service or self.auto:return
        args=(ids,self.goal.value(),self.speed.value(),self.acc.value(),self.time_raw.value(),self.method.currentData())
        self.pending_manual=('servo',args);self.tick()
    def dispatch_control(self,args):
        ids=args[0]
        if self.torque.isChecked():self.commanded.update(ids)
        self.submit('指令送信',lambda cancel:self.service.control(*args,cancel=cancel))
    @after_monitor
    def action(self):
        if Q.QMessageBox.question(self,'Action','バス全体の登録済み指令を実行します。続けますか？',Q.QMessageBox.Yes|Q.QMessageBox.Cancel,Q.QMessageBox.Cancel)==Q.QMessageBox.Yes:self.submit('Action',lambda cancel:self.service.action())
    @after_monitor
    def torque_change(self,checked):
        ids=self.ids()
        if checked:self.commanded.update(ids)
        self.submit('トルクON' if checked else 'トルクOFF',lambda cancel:self.service.set_torque(ids,checked),lambda _:self.torque_done(ids,checked))
        if not checked:self.off_attempt=ids
    def torque_done(self,ids,enabled):
        if not enabled:self.commanded.difference_update(ids);self.uncertain.difference_update(ids)
        self.torque.setChecked(enabled)
    def stop_all(self):
        self.cancel_auto(silent=True);self.test_active=False;self.test_button.setText('Test / 開始');self.pending_manual=None;self.pending_ui.clear();self.worker.cancel.set()
        if self.adapter_mode==0 or self.tabs.currentIndex()==3:self.pending_pwm_off=True
        ids=sorted(set(self.ids())|self.commanded|self.uncertain|(self.service.pending if self.service else set()))
        if not ids:
            if self.pending_pwm_off:self.tick()
            else:self.note('停止対象がありません')
            return
        self.pending_off=ids;self.tick()
    def torque_off(self,ids):
        self.off_attempt=ids
        def stopped(_):
            self.torque_done(ids,False);self.health.setText('対象トルクOFF 確認済み')
            if self.tabs.currentIndex()==3:self.pending_mode=0
            if self.service.pending:self.note('登録済み指令は残っています。トルクOFFを維持してください。')
        self.submit('トルクOFF',lambda cancel:self.service.set_torque(ids,False),stopped)
    def begin_auto(self,step):
        if self.auto:self.cancel_auto();return
        if self.method.currentData()=='registered':self.note('自動動作はWriteまたはSync Writeを選んでください');return
        try:pattern=Pattern(self.start_value.value(),self.end_value.value(),self.step_size.value() if step else None,clamp=False)
        except ValueError as e:self.note(str(e));return
        self.auto={'pattern':pattern,'ids':self.ids(),'speed':self.speed.value(),'acc':self.acc.value(),'time':self.time_raw.value(),'method':self.method.currentData(),'delay':(self.step_delay.value() if step else self.sweep_delay.value())/1000,'next':0,'pwm':False}
        self.update_controls();self.tick()
    def cancel_auto(self,silent=False):
        self.auto=None;self.update_controls()
        if not silent:self.note('自動動作を停止しました（トルク状態は維持）')
    def auto_tick(self):
        a=self.auto;value=a['pattern'].next()
        def done(_):
            if self.auto is a:a['next']=time.monotonic()+a['delay']
        if a['pwm']:self.submit('PWM自動',lambda cancel:self.service.pwm('pulse',value),done,True)
        else:
            self.goal.setValue(value);self.submit('自動動作',lambda cancel:self.service.control(a['ids'],value,a['speed'],a['acc'],a['time'],a['method'],cancel=cancel),done,True)
    def series_toggle(self,key,checked):
        if checked:self.trend.visible.add(key)
        else:self.trend.visible.discard(key)
        self.trend.update()
    def plot_config(self):
        self.trend.window=self.window_s.value();self.trend.offset=self.offset_s.value();self.trend.bounds=(self.lower.value(),self.upper.value());self.trend.update()
    def capture_toggle(self):
        if self.capture:self.capture_finish();return
        path,kind=Q.QFileDialog.getSaveFileName(self,'記録先','record.txt','テキスト (*.txt);;CSV (*.csv)')
        if not path:return
        try:recorder=Recorder(path,kind.startswith('テキスト'))
        except Exception as e:self.note('記録先を開けません: '+str(e));return
        self.capture_rows=[];self.capture={'recorder':recorder,'path':path,'interval':self.capture_seconds.value(),'flush_at':time.monotonic()+self.capture_seconds.value()};self.capture_count.setText('0 rows');self.export_button.setText('記録停止');self.monitor.setChecked(True)
    def capture_finish(self):
        if not self.capture:return
        info=self.capture;self.capture=None;self.export_button.setText('Export / 記録')
        try:info['recorder'].flush();self.note(f'{len(self.capture_rows)}行を保存: {info["path"]}')
        except Exception as e:self.note('保存失敗（記録保持）: '+str(e))
    def save_capture(self):
        path,_=Q.QFileDialog.getSaveFileName(self,'現在の記録を保存','record.csv','CSV (*.csv)')
        if path:
            try:write_csv(path,self.capture_rows);self.note('保存: '+path)
            except Exception as e:self.note(str(e))
    def clear_data(self):
        if self.capture:self.notice('記録を停止してからEmptyを実行してください');return
        self.capture_rows=[];self.capture_count.setText('0 rows');self.trend.rows.clear();self.trend.update()
    @after_monitor
    def save_parameter(self):
        i=self.memory.currentRow()
        if i<0:return
        address=int(self.memory.item(i,0).text())
        try:value=int(self.memory.item(i,3).text());r=self.service.get(self.current).profile.field(address);r.pack(value,self.service.get(self.current).profile.order)
        except Exception as e:self.note(str(e));return
        if Q.QMessageBox.question(self,'設定保存',f'ID {self.current} / {r.name}\n{self.memory.item(i,2).text()} → {value}\n書き込みますか？',Q.QMessageBox.Yes|Q.QMessageBox.Cancel,Q.QMessageBox.Cancel)!=Q.QMessageBox.Yes:return
        sid=self.current
        if address in (40,41,42,44,46) and not (address==40 and value==0):self.commanded.add(sid)
        def write(cancel):
            new=self.service.write_register(sid,address,value);return new,self.service.snapshot(new)
        def done(result):
            new,snapshot=result;self.current=new
            for j in range(self.servos.topLevelItemCount()):
                item=self.servos.topLevelItem(j)
                if int(item.text(0))==sid:item.setText(0,str(new))
            if address==40 and value==0:self.torque_done([new],False)
            self.show_memory(snapshot)
        self.submit('設定保存',write,done)
    @after_monitor
    def save_image(self):
        if self.service.get(self.current).profile.family!='STS':self.notice('xdat設定ファイルはSTSに対応しています');return
        path,_=Q.QFileDialog.getSaveFileName(self,'Save xdat','servo.xdat','STS parameters (*.xdat)')
        if not path:return
        def done(result):ParameterImage(0,result['raw'][:40]).save(path);self.note('xdat保存: '+path)
        self.submit('設定ファイル保存',lambda cancel:self.service.snapshot(self.current),done)
    @after_monitor
    def load_image(self):
        path,_=Q.QFileDialog.getOpenFileName(self,'Load xdat','','STS parameters (*.xdat)')
        if not path:return
        try:image=ParameterImage.load(path)
        except Exception as e:self.note(str(e));return
        def preview(result):
            self.snapshot=result
            try:changes=image.changes(self.service.get(self.current),result['values'])
            except Exception as e:self.note(str(e));return
            dialog=Q.QDialog(self);dialog.setWindowTitle('復元する差分を選択');dialog.resize(620,440);layout=Q.QVBoxLayout(dialog);table=Q.QTableWidget(len(changes),4);table.setHorizontalHeaderLabels(['適用','項目','現在','復元値']);table.horizontalHeader().setSectionResizeMode(1,Q.QHeaderView.Stretch)
            for i,(a,v) in enumerate(changes):
                check=Q.QTableWidgetItem();check.setFlags(C.Qt.ItemIsEnabled|C.Qt.ItemIsUserCheckable);check.setCheckState(C.Qt.Unchecked if a in (5,6) else C.Qt.Checked);table.setItem(i,0,check)
                for j,text in enumerate([self.service.get(self.current).profile.field(a).name,str(result['values'][a]),str(v)],1):
                    item=Q.QTableWidgetItem(text);item.setFlags(C.Qt.ItemIsEnabled);table.setItem(i,j,item)
            layout.addWidget(table);layout.addWidget(Q.QLabel('EEPROM復元はトルクOFFで実行。ID/通信速度は初期選択から除外。'))
            buttons=Q.QDialogButtonBox(Q.QDialogButtonBox.Ok|Q.QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
            if dialog.exec_()==Q.QDialog.Accepted:
                selected=[pair for i,pair in enumerate(changes) if table.item(i,0).checkState()==C.Qt.Checked]
                selected.sort(key=lambda pair:(pair[0] in (5,6),pair[0]));sid=self.current
                def done(r):
                    self.current=r['id'];self.servos.blockSignals(True);self.servos.clear()
                    for servo in self.service.servos.values():
                        item=self.add_servo(servo)
                        if servo.sid==self.current:item.setSelected(True)
                    self.servos.blockSignals(False);self.note(str(r));C.QTimer.singleShot(0,self.read_memory)
                C.QTimer.singleShot(0,lambda:self.submit('設定復元',lambda cancel:self.service.restore(sid,selected,cancel),done))
        self.submit('復元前読取',lambda cancel:self.service.snapshot(self.current),preview)
    @after_monitor
    def recovery(self):
        sid=self.current
        if Q.QMessageBox.warning(self,'Recovery',f'ID {sid} に初期化指令を送信します。設定が失われる可能性があります。\n復帰先ID・通信速度と完了状態は保証できません。続けますか？',Q.QMessageBox.Yes|Q.QMessageBox.Cancel,Q.QMessageBox.Cancel)!=Q.QMessageBox.Yes:return
        self.monitor.setChecked(False)
        def done(message):self.current=None;self.snapshot=None;self.servos.clear();self.notice(message)
        self.submit('Recovery送信',lambda cancel:self.service.reset(sid),done)
    @after_monitor
    def calibrate(self):
        if Q.QMessageBox.question(self,'中点校正','現在位置を2048に校正します。基準位置とトルクOFFを確認してください。',Q.QMessageBox.Yes|Q.QMessageBox.Cancel,Q.QMessageBox.Cancel)==Q.QMessageBox.Yes:self.submit('中点校正',lambda cancel:self.service.calibration(self.current),lambda _:C.QTimer.singleShot(0,self.read_memory))
    def toggle_test(self):
        self.test_active=not self.test_active;self.next_test=0;self.test_button.setText('Stop / 停止' if self.test_active else 'Test / 開始');self.update_controls()
    def clear_test(self):self.stats=CommunicationStats();self.test_output.clear()
    def test_tick(self):
        sid=self.current
        def work(cancel):
            before=self.service.link.tx_bytes+self.service.link.rx_bytes;start=time.monotonic()
            try:self.service.feedback(sid);kind='success'
            except Timeout:kind='timeout'
            elapsed=time.monotonic()-start;return elapsed,self.service.link.tx_bytes+self.service.link.rx_bytes-before,kind
        def done(result):
            self.next_test=time.monotonic()+(.05 if result[2]!='success' else 0);self.stats.add(*result);r=self.stats.report();self.test_output.setPlainText(f'ID {sid}\n試行 {r["attempts"]} / 成功 {r["success"]} / Timeout {r["timeouts"]}\n応答 min {r["min_us"]:.0f} / mean {r["mean_us"]:.0f} / max {r["max_us"]:.0f} µs\n実効速度 {r["kbps"]:.2f} kb/s')
        self.submit('通信試験',work,done,True)
    def open_firmware(self):
        path,_=Q.QFileDialog.getOpenFileName(self,'Firmware','','Firmware (*.hex *.bin *.fbin *.mbin *.xbin);;All (*)')
        if path:
            try:self.firmware_output.setPlainText(json.dumps(inspect_firmware(path),ensure_ascii=False,indent=2)+'\n\nUpgrade転送は未対応です。')
            except Exception as e:self.firmware_output.setPlainText(str(e))
    @after_monitor
    def pwm_command(self,kind,value):
        if not self.service:return
        self.test_active=False
        if kind=='pulse':
            self.pulse.setValue(value);self.pwm_slider.blockSignals(True);self.pwm_slider.setValue(value);self.pwm_slider.blockSignals(False)
        self.submit('PWM送信',lambda cancel:self.service.pwm(kind,value),self.note)
    def begin_pwm_auto(self,step):
        try:pattern=Pattern(self.pwm_min.value(),self.pwm_max.value(),self.pwm_step.value() if step else None)
        except ValueError as e:self.note(str(e));return
        self.test_active=False;self.auto={'pattern':pattern,'pwm':True,'delay':self.pwm_delay.value()/1000,'next':0};self.update_controls()
    def closeEvent(self,event):
        self.cancel_auto(silent=True);self.test_active=False;self.monitor.setChecked(False)
        if self.busy:self.closing=True;self.worker.cancel.set();event.ignore();return
        if self.commanded or self.uncertain or (self.service and self.service.pending):
            text='トルクON・停止未確認・登録指令のいずれかが残っています。\nSTOPで確認してから終了することを推奨します。このまま終了しますか？'
            if Q.QMessageBox.question(self,'終了',text,Q.QMessageBox.Yes|Q.QMessageBox.Cancel,Q.QMessageBox.Cancel)!=Q.QMessageBox.Yes:self.closing=False;event.ignore();return
        self.capture_finish();self.pending_manual=None;self.timer.stop()
        if self.service:self.service.link.close()
        self.worker.close();event.accept()

def main(argv=None):
    import sys
    args=sys.argv if argv is None else argv;app=Q.QApplication(args);app.setStyle('Fusion');app.setFont(G.QFont('Noto Sans CJK JP',9))
    app.setStyleSheet('QGroupBox {font-weight:600;margin-top:8px;border:1px solid #cdd5df;border-radius:4px;padding:10px 6px 6px;} QGroupBox::title {subcontrol-origin:margin;left:8px;} QPushButton {padding:5px 8px;} QTabBar::tab {padding:8px 12px;} QMainWindow {background:#f4f6f9;}')
    window=Window('--demo' in args);window.show()
    if '--smoke' in args:C.QTimer.singleShot(600,window.close)
    return app.exec_()
