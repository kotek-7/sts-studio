"""Widget layout. Device operations live in feature controllers."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING

from PySide6 import QtCore as C
from PySide6 import QtGui as G
from PySide6 import QtWidgets as Q

from ..catalog import PROTOCOL, ROOT
from .signals import bind_click
from .trend import SERIES, Trend
from .widgets import required

if TYPE_CHECKING:
    from .connection import ConnectionController
    from .diagnostics import DiagnosticsController
    from .monitoring import MonitoringController
    from .motion import MotionController
    from .programming import ProgrammingController
    from .pwm import PwmController


class DesktopView(Q.QMainWindow):
    connections: ConnectionController
    programming: ProgrammingController
    motion: MotionController
    monitoring: MonitoringController
    diagnostics: DiagnosticsController
    pwm: PwmController
    motion_buttons: list[Q.QPushButton]
    device_buttons: list[Q.QPushButton]

    def note(self, text: str) -> None:
        raise NotImplementedError

    def bind_action(self, button: Q.QAbstractButton, callback: Callable[[], object]) -> None:
        bind_click(button, callback, self.note)

    def build_ui(self, demo: bool = False) -> None:
        w: Q.QWidget
        main = Q.QWidget()
        self.setCentralWidget(main)
        outer = Q.QVBoxLayout(main)
        outer.setContentsMargins(14, 12, 14, 8)
        title = Q.QHBoxLayout()
        label = Q.QLabel("STS Studio")
        label.setStyleSheet("font-size:22px;font-weight:700;color:#163453")
        title.addWidget(label)
        title.addWidget(Q.QLabel("サーボ設定・モニター"))
        title.addStretch()
        self.state_label = Q.QLabel("DISCONNECTED")
        title.addWidget(self.state_label)
        outer.addLayout(title)
        split = Q.QSplitter()
        outer.addWidget(split, 1)
        sidebar = Q.QWidget()
        side = Q.QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 8, 0)
        group = Q.QGroupBox("Com Settings / 接続")
        form = Q.QFormLayout(group)
        self.port = Q.QComboBox()
        self.port.setMinimumWidth(190)
        self.refresh = Q.QPushButton("更新")
        self.bind_action(self.refresh, self.connections.ports)
        portrow = Q.QWidget()
        pr = Q.QHBoxLayout(portrow)
        pr.setContentsMargins(0, 0, 0, 0)
        pr.addWidget(self.port, 1)
        pr.addWidget(self.refresh)
        self.baud = Q.QComboBox()
        self.baud.addItems([str(v) for v in PROTOCOL["port"]["baud_choices"]])
        self.baud.setCurrentText("115200")
        self.parity = Q.QComboBox()
        self.parity.addItems(["N", "O", "E"])
        self.timeout = self.spin(5, 5000, 50)
        self.demo = Q.QCheckBox("デモ（実機通信なし）")
        self.demo.setChecked(demo)
        self.connection = Q.QPushButton("Open / 接続")
        self.bind_action(self.connection, self.connections.toggle_connection)
        for name, w in [
            ("Port", portrow),
            ("Baud", self.baud),
            ("Parity", self.parity),
            ("Timeout ms", self.timeout),
            ("", self.demo),
            ("", self.connection),
        ]:
            form.addRow(name, w)
        side.addWidget(group)
        group = Q.QGroupBox("Servo List / サーボ")
        lv = Q.QVBoxLayout(group)
        bounds = Q.QHBoxLayout()
        self.first = self.spin(0, 253, 0)
        self.last = self.spin(0, 253, 253)
        bounds.addWidget(self.first)
        bounds.addWidget(Q.QLabel("〜"))
        bounds.addWidget(self.last)
        lv.addLayout(bounds)
        self.search = Q.QPushButton("Search / 検索")
        self.bind_action(self.search, self.connections.scan)
        lv.addWidget(self.search)
        self.scan_status = Q.QLabel("未検索")
        lv.addWidget(self.scan_status)
        self.servos = Q.QTreeWidget()
        self.servos.setHeaderLabels(["ID", "Model", "FW"])
        self.servos.setSelectionMode(Q.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.servos.setColumnWidth(0, 40)
        self.servos.setColumnWidth(1, 120)
        self.servos.itemSelectionChanged.connect(self.connections.selection_changed)
        lv.addWidget(self.servos, 1)
        lv.addWidget(Q.QLabel("Ctrl / Shiftで複数台を選択"))
        direct = Q.QHBoxLayout()
        self.direct_id = self.spin(0, 253, 1)
        self.identify_button = Q.QPushButton("ID指定")
        self.bind_action(self.identify_button, self.connections.identify)
        direct.addWidget(self.direct_id)
        direct.addWidget(self.identify_button)
        lv.addLayout(direct)
        side.addWidget(group, 1)
        self.off = Q.QPushButton("STOP / トルク・PWM OFF")
        self.off.setStyleSheet("background:#a32020;color:white;font-weight:bold;padding:10px")
        self.bind_action(self.off, self.motion.stop_all)
        side.addWidget(self.off)
        split.addWidget(sidebar)
        self.tabs = Q.QTabWidget()
        split.addWidget(self.tabs)
        split.setSizes([290, 940])
        self.build_debug()
        self.build_programming()
        self.build_upgrade()
        self.build_pwm()
        self.build_log()

    @staticmethod
    def spin(lo: int, hi: int, value: int) -> Q.QSpinBox:
        s = Q.QSpinBox()
        s.setRange(lo, hi)
        s.setValue(value)
        return s

    def button(self, text: str, fn: Callable[[], object], kind: str = "device") -> Q.QPushButton:
        b = Q.QPushButton(text)
        self.bind_action(b, fn)
        if kind == "device":
            self.device_buttons.append(b)
        elif kind == "motion":
            self.motion_buttons.append(b)
        return b

    def tab(self, title: str) -> Q.QVBoxLayout:
        content = Q.QWidget()
        layout = Q.QVBoxLayout(content)
        layout.setSpacing(9)
        scroll = Q.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(Q.QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        self.tabs.addTab(scroll, title)
        return layout

    def build_debug(self) -> None:
        lay = self.tab("Debug / 操作")
        top = Q.QHBoxLayout()
        self.trend = Trend()
        top.addWidget(self.trend, 1)
        controls = Q.QGridLayout()
        for index, (key, (name, color)) in enumerate(SERIES.items()):
            c = Q.QCheckBox(name)
            c.setChecked(key in self.trend.visible)
            c.setStyleSheet("color:" + color)
            c.toggled.connect(lambda checked, k=key: self.monitoring.series_toggle(k, checked))
            controls.addWidget(c, index // 2, index % 2)
        self.window_s = self.spin(1, 600, 30)
        self.offset_s = self.spin(0, 600, 0)
        self.plot_lower = Q.QDoubleSpinBox()
        self.upper = Q.QDoubleSpinBox()
        for bound in [self.plot_lower, self.upper]:
            bound.setRange(-1000000000.0, 1000000000.0)
            bound.valueChanged.connect(self.monitoring.plot_config)
        self.window_s.valueChanged.connect(self.monitoring.plot_config)
        self.offset_s.valueChanged.connect(self.monitoring.plot_config)
        for index, (name, w) in enumerate(
            [
                ("表示幅 秒", self.window_s),
                ("過去へ 秒", self.offset_s),
                ("Low", self.plot_lower),
                ("Up（0=auto）", self.upper),
            ]
        ):
            controls.addWidget(Q.QLabel(name), 4 + index, 0)
            controls.addWidget(w, 4 + index, 1)
        top.addLayout(controls)
        lay.addLayout(top, 1)
        middle = Q.QHBoxLayout()
        control = Q.QGroupBox("Servo Control")
        cl = Q.QGridLayout(control)
        self.method = Q.QComboBox()
        self.method.addItem("Write", "write")
        self.method.addItem("Sync Write", "sync")
        self.method.addItem("Reg Write", "registered")
        cl.addWidget(self.method, 0, 0, 1, 2)
        self.torque = Q.QCheckBox("Torque Enable")
        self.torque.clicked.connect(self.motion.torque_change)
        cl.addWidget(self.torque, 0, 2, 1, 2)
        self.slider = Q.QSlider(C.Qt.Orientation.Horizontal)
        self.slider.setRange(0, 4095)
        self.slider.setValue(2047)
        self.slider.valueChanged.connect(self.motion.slider_changed)
        cl.addWidget(self.slider, 1, 0, 1, 4)
        self.acc = self.spin(0, 254, 0)
        self.goal = self.spin(-32766, 32766, 2047)
        self.speed = self.spin(-32766, 32766, 0)
        self.time_raw = self.spin(0, 65535, 0)
        self.goal.valueChanged.connect(self.motion.goal_changed)
        for row, name, w, col in [
            (2, "Acc", self.acc, 0),
            (2, "Goal", self.goal, 2),
            (3, "Speed", self.speed, 0),
            (3, "Time (raw)", self.time_raw, 2),
        ]:
            cl.addWidget(Q.QLabel(name), row, col)
            cl.addWidget(w, row, col + 1)
        self.live = Q.QCheckBox("Live（スライダー操作で送信）")
        self.live.setChecked(True)
        cl.addWidget(self.live, 4, 0, 1, 4)
        cl.addWidget(self.button("Set / 送信", self.motion.send, "motion"), 5, 0, 1, 2)
        cl.addWidget(self.button("Action", self.motion.action, "motion"), 5, 2, 1, 2)
        middle.addWidget(control, 1)
        feedback = Q.QGroupBox("Servo Feedback")
        fl = Q.QGridLayout(feedback)
        self.values: dict[int | str, Q.QLabel] = {}
        feedback_fields: list[tuple[int | str, str]] = [
            (62, "Voltage [V]"),
            (60, "Torque [raw]"),
            (69, "Current [raw]"),
            (58, "Speed [step/s]"),
            (63, "Temperature [°C]"),
            (56, "Position [step]"),
            (66, "Moving"),
            ("goal", "Goal"),
        ]
        for i, (key, name) in enumerate(feedback_fields):
            value = Q.QLabel("—")
            value.setStyleSheet("font-size:15px;font-weight:600")
            fl.addWidget(Q.QLabel(name), i // 2, i % 2 * 2)
            fl.addWidget(value, i // 2, i % 2 * 2 + 1)
            self.values[key] = value
        self.health = Q.QLabel("未読取")
        self.health.setWordWrap(True)
        fl.addWidget(self.health, 4, 0, 1, 4)
        self.monitor = Q.QCheckBox("モニター")
        self.period = self.spin(20, 5000, 50)
        fl.addWidget(self.monitor, 5, 0, 1, 2)
        fl.addWidget(self.period, 5, 2, 1, 2)
        middle.addWidget(feedback, 1)
        lay.addLayout(middle)
        bottom = Q.QHBoxLayout()
        auto = Q.QGroupBox("Auto debug")
        al = Q.QGridLayout(auto)
        self.start_value = self.spin(-32766, 32766, 0)
        self.end_value = self.spin(-32766, 32766, 4095)
        self.sweep_delay = self.spin(10, 600000, 2500)
        self.step_size = self.spin(1, 32766, 4)
        self.step_delay = self.spin(10, 600000, 20)
        self.step_size.setToolTip("Stepは端点を跨いだ指令を送信してから折り返します")
        for row, name, w, col in [
            (0, "Start", self.start_value, 0),
            (1, "End", self.end_value, 0),
            (0, "Sweep ms", self.sweep_delay, 2),
            (1, "Step", self.step_size, 2),
            (2, "Step ms", self.step_delay, 2),
        ]:
            al.addWidget(Q.QLabel(name), row, col)
            al.addWidget(w, row, col + 1)
        al.addWidget(self.button("Sweep", lambda: self.motion.begin_auto(False), "motion"), 0, 4)
        al.addWidget(self.button("Step", lambda: self.motion.begin_auto(True), "motion"), 1, 4)
        stop = Q.QPushButton("自動動作中止")
        self.bind_action(stop, self.motion.cancel_auto)
        al.addWidget(stop, 2, 4)
        bottom.addWidget(auto, 3)
        data = Q.QGroupBox("Data analysis")
        dl = Q.QFormLayout(data)
        self.capture_seconds = self.spin(1, 86400, 30)
        dl.addRow("保存間隔 [s]", self.capture_seconds)
        self.capture_count = Q.QLabel("0 rows")
        dl.addRow(self.capture_count)
        dr = Q.QHBoxLayout()
        self.export_button = Q.QPushButton("Export / 記録")
        self.bind_action(self.export_button, self.monitoring.capture_toggle)
        dr.addWidget(self.export_button)
        empty = Q.QPushButton("Empty")
        self.bind_action(empty, self.monitoring.clear_data)
        dr.addWidget(empty)
        dl.addRow(dr)
        save = Q.QPushButton("現在の記録を保存")
        self.bind_action(save, self.monitoring.save_capture)
        dl.addRow(save)
        bottom.addWidget(data, 2)
        lay.addLayout(bottom)

    def build_programming(self) -> None:
        lay = self.tab("Programming / 設定")
        row = Q.QHBoxLayout()
        for text, fn in [
            ("Read / 再読込", self.programming.read_memory),
            ("Save .xdat", self.programming.save_image),
            ("Load .xdat", self.programming.load_image),
            ("Recovery", self.programming.recovery),
            ("中点校正", self.programming.calibrate),
        ]:
            row.addWidget(self.button(text, fn))
        lay.addLayout(row)
        self.memory = Q.QTableWidget(0, 7)
        self.memory.setHorizontalHeaderLabels(
            ["Addr", "Memory", "Value", "Edit", "Area", "R/W", "Range"]
        )
        self.memory.setSelectionBehavior(Q.QAbstractItemView.SelectionBehavior.SelectRows)
        self.memory.setSelectionMode(Q.QAbstractItemView.SelectionMode.SingleSelection)
        self.memory.itemSelectionChanged.connect(self.programming.describe_register)
        required(self.memory.horizontalHeader()).setSectionResizeMode(
            1, Q.QHeaderView.ResizeMode.Stretch
        )
        for i, width in [(0, 48), (2, 80), (3, 80), (4, 70), (5, 45), (6, 125)]:
            self.memory.setColumnWidth(i, width)
        lay.addWidget(self.memory, 1)
        self.parameter_description = Q.QLabel("項目を選択すると範囲と格納形式を表示します")
        self.parameter_description.setWordWrap(True)
        lay.addWidget(self.parameter_description)
        lay.addWidget(self.button("選択した行の編集値を保存", self.programming.save_parameter))
        label = Q.QLabel("EEPROMの保存にはトルクOFFが必要です。変更後の値は読み戻して確認します。")
        label.setWordWrap(True)
        lay.addWidget(label)

    def build_upgrade(self) -> None:
        lay = self.tab("診断・ファイル検査")
        group = Q.QGroupBox("Communication test")
        gl = Q.QVBoxLayout(group)
        self.test_output = Q.QPlainTextEdit()
        self.test_output.setReadOnly(True)
        self.test_output.setMaximumBlockCount(500)
        gl.addWidget(self.test_output)
        row = Q.QHBoxLayout()
        self.test_button = Q.QPushButton("Test / 開始")
        self.bind_action(self.test_button, self.diagnostics.toggle_test)
        row.addWidget(self.test_button)
        clear = Q.QPushButton("Clear")
        self.bind_action(clear, self.diagnostics.clear_test)
        row.addWidget(clear)
        gl.addLayout(row)
        lay.addWidget(group, 1)
        group = Q.QGroupBox("Firmware update")
        fl = Q.QVBoxLayout(group)
        self.firmware_output = Q.QPlainTextEdit()
        self.firmware_output.setReadOnly(True)
        self.firmware_output.setPlainText(
            "ファームウェアの検査に対応しています。\nファームウェアの書き込みには対応していません。"
        )
        fl.addWidget(self.firmware_output)
        row = Q.QHBoxLayout()
        openfile = Q.QPushButton("Open / ファイル検査")
        self.bind_action(openfile, self.diagnostics.open_firmware)
        row.addWidget(openfile)
        fl.addLayout(row)
        lay.addWidget(group, 1)

    def build_pwm(self) -> None:
        lay = self.tab("PWM / アダプター")
        description = Q.QLabel(
            "対応アダプターのID253を操作します。サーボへのPWMモード設定とは別機能です。\n実機でのPWM出力は未検証です。"
        )
        description.setWordWrap(True)
        lay.addWidget(description)
        row = Q.QHBoxLayout()
        self.pwm_mode = Q.QPushButton("PWMモードへ")
        self.bind_action(self.pwm_mode, lambda: self.pwm.pwm_command("mode", 0))
        row.addWidget(self.pwm_mode)
        self.bus_mode = Q.QPushButton("バスモードへ戻す")
        self.bind_action(self.bus_mode, lambda: self.pwm.pwm_command("mode", 1))
        row.addWidget(self.bus_mode)
        lay.addLayout(row)
        self.pwm_slider = Q.QSlider(C.Qt.Orientation.Horizontal)
        self.pwm_slider.setRange(500, 2500)
        self.pwm_slider.setValue(1500)
        self.pwm_slider.valueChanged.connect(self.pwm.pwm_slide)
        lay.addWidget(self.pwm_slider)
        self.pulse = self.spin(500, 2500, 1500)
        form = Q.QFormLayout()
        form.addRow("Pulse [µs]", self.pulse)
        lay.addLayout(form)
        row = Q.QHBoxLayout()
        self.pwm_buttons = []
        for value in [500, 900, 1200, 1500, 1800, 2100, 2500]:
            b = Q.QPushButton(str(value))
            self.bind_action(b, partial(self.pwm.pwm_command, "pulse", value))
            row.addWidget(b)
            self.pwm_buttons.append(b)
        lay.addLayout(row)
        row = Q.QHBoxLayout()
        for label, fn in [
            ("Pulse送信", lambda: self.pwm.pwm_command("pulse", self.pulse.value())),
            ("出力ON", lambda: self.pwm.pwm_command("enable", 1)),
            ("出力OFF", lambda: self.pwm.pwm_command("enable", 0)),
        ]:
            b = Q.QPushButton(label)
            self.bind_action(b, fn)
            row.addWidget(b)
            self.pwm_buttons.append(b)
        lay.addLayout(row)
        group = Q.QGroupBox("自動動作 / パルス範囲")
        form = Q.QFormLayout(group)
        self.pwm_min = self.spin(500, 2500, 500)
        self.pwm_max = self.spin(500, 2500, 2500)
        self.pwm_delay = self.spin(10, 600000, 1000)
        self.pwm_step = self.spin(1, 2000, 4)
        for label, w in [
            ("Min µs", self.pwm_min),
            ("Max µs", self.pwm_max),
            ("Delay ms", self.pwm_delay),
            ("Step µs", self.pwm_step),
        ]:
            form.addRow(label, w)
        row = Q.QHBoxLayout()
        for label, fn in [
            ("Sweep", lambda: self.pwm.begin_pwm_auto(False)),
            ("Step", lambda: self.pwm.begin_pwm_auto(True)),
            ("中止", self.motion.cancel_auto),
        ]:
            b = Q.QPushButton(label)
            self.bind_action(b, fn)
            row.addWidget(b)
            self.pwm_buttons.append(b)
        form.addRow(row)
        lay.addWidget(group)
        lay.addStretch()

    def build_log(self) -> None:
        lay = self.tab("通信ログ")
        self.packet_logging = Q.QCheckBox("HEXパケットをログに含める")
        lay.addWidget(self.packet_logging)
        self.log = Q.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)
        lay.addWidget(self.log)
        row = Q.QHBoxLayout()
        spec = Q.QPushButton("仕様書を開く")
        self.bind_action(
            spec,
            lambda: G.QDesktopServices.openUrl(
                C.QUrl.fromLocalFile(str(ROOT / "docs/SPECIFICATION.md"))
            ),
        )
        row.addWidget(spec)
        matrix = Q.QPushButton("機能一覧を開く")
        self.bind_action(
            matrix,
            lambda: G.QDesktopServices.openUrl(
                C.QUrl.fromLocalFile(str(ROOT / "docs/FEATURE_MATRIX.md"))
            ),
        )
        row.addWidget(matrix)
        lay.addLayout(row)
