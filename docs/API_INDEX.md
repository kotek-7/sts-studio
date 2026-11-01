# モジュール・関数索引

モジュール別のシグネチャと定義行を示します。動作仕様はSPECIFICATION / DESIGNを参照してください。

## __init__.py

STS Studio servo configuration and monitoring application.

## __main__.py

Keep the desktop default while loading CLI without Qt.

## automation.py

Pure scheduling/statistics models; no I/O and no sleeping inside the UI thread.

### Pattern

- `Pattern.__init__(self, start: int, end: int, step: int | None=None, clamp: bool=True)` — line 10
- `Pattern.next(self)` — line 23

### CommunicationStats

- `CommunicationStats.add(self, seconds: float, bytes_count: int, kind: str='success')` — line 59
- `CommunicationStats.report(self)` — line 73

## catalog.py

Register definitions, model identification, and value encoding.

- `unsigned_word(value: int, order: Literal['little', 'big']='little', sign_bit: int=-1)` — line 15
- `decode(data: bytes | bytearray, order: Literal['little', 'big']='little', sign_bit: int=-1)` — line 25
### Register

- `Register.from_dict(cls, d: dict[str, Any])` — line 45
- `Register.writable(self)` — line 49
- `Register.limits(self)` — line 53
- `Register.pack(self, value: int, order: Literal['little', 'big'])` — line 60
- `Register.unpack(self, raw: bytes, order: Literal['little', 'big'])` — line 67

### Profile

- `Profile.__init__(self, data: dict[str, Any])` — line 72
- `Profile.decode_memory(self, data: bytes, base: int=0)` — line 88
- `Profile.field(self, a: int)` — line 95

- `identify(header: bytes)` — line 101
## cli/__init__.py

Headless command line entry point; imports no Qt modules.

- `json_default(value: object)` — line 21
- `emit(value: object)` — line 27
- `main(argv: Sequence[str] | None=None)` — line 31
## cli/commands.py

Synchronous CLI workflows using the same service as the desktop UI.

- `describe(servo: Servo)` — line 18
- `stop_targets(service: Service, targets: list[int], emit: Emit)` — line 28
- `execute(args: argparse.Namespace, service: Service, emit: Emit)` — line 41
## cli/parser.py

CLI syntax and validation, performed before opening a serial port.

- `integer_range(low: int, high: int)` — line 12
- `ids(text: str)` — line 25
- `build_parser()` — line 32
## contracts.py

Transport and result contracts shared by real and simulated connections.

### Link

- `Link.close(self)` — line 14
- `Link.exchange(self, sid: int, ins: int, params: bytes=b'', expected: int=0, wait: bool=True)` — line 15

### Feedback


### Snapshot


### RestoreResult


## files.py

Strict, non-executing file formats. Xdat support is limited to STS parameter blocks.

### ParameterImage

- `ParameterImage.load(cls, path)` — line 16
- `ParameterImage.save(self, path)` — line 25
- `ParameterImage.changes(self, servo, current)` — line 30

- `csv_row(row, index, legacy)` — line 60
- `write_csv(path, rows, legacy=False)` — line 87
### Recorder

- `Recorder.__init__(self, path, legacy=False)` — line 98
- `Recorder.append(self, row)` — line 105
- `Recorder.flush(self)` — line 109

- `inspect_firmware(path)` — line 119
## jobs.py

Single-flight worker with bounded admission and per-operation cancellation.

### Worker

- `Worker.__init__(self)` — line 21
- `Worker.submit(self, token: int, function: Work)` — line 29
- `Worker._run(self, token: int, function: Work, cancel: threading.Event)` — line 40
- `Worker.cancel_current(self)` — line 52
- `Worker.close(self)` — line 56

## runtime/__init__.py

Execution and connection state independent of feature widgets.

## runtime/executor.py

GUI-thread execution state, completion routing, and bounded UI admission.

### JobKind


### Job


### Executor

- `Executor.__init__(self, worker: Worker, parent: QObject | None=None)` — line 36
- `Executor.busy(self)` — line 47
- `Executor.monitoring(self)` — line 51
- `Executor.interactive(self)` — line 55
- `Executor.submit(self, name: str, fn: Work, done: Callable[[Any], None] | None=None, quiet: bool=False, *, kind: JobKind=JobKind.FOREGROUND)` — line 58
- `Executor.defer_ui(self, action: Callable[[], None])` — line 80
- `Executor.run_pending(self)` — line 91
- `Executor.discard_pending(self)` — line 101
- `Executor.cancel_current(self)` — line 104
- `Executor._done(self, token: int, result: Any)` — line 108
- `Executor._failed(self, token: int, error: Exception)` — line 125
- `Executor.close(self)` — line 134

## runtime/session.py

Single owner of connection identity and unconfirmed actuator state.

### Session

- `Session.require_service(self)` — line 20
- `Session.require_id(self)` — line 25

## service.py

Servo operations. No Qt dependencies; effects and partial failures are explicit.

### Servo

- `Servo.require_profile(self)` — line 22
- `Servo.firmware(self)` — line 28

### Service

- `Service.__init__(self, link: Link)` — line 33
- `Service.discover(self, sid: int)` — line 39
- `Service.scan(self, start: int, end: int, cancel: Event, progress: Callable[[int, Servo | None], None])` — line 46
- `Service.get(self, sid: int)` — line 63
- `Service.snapshot(self, sid: int)` — line 71
- `Service.feedback(self, sid: int)` — line 90
- `Service.read_value(self, sid: int, address: int)` — line 112
- `Service.verify(self, sid: int, address: int, data: bytes, ignore_alarm: bool=False)` — line 118
- `Service.write_verified(self, sid: int, address: int, data: bytes, ignore_alarm: bool=False)` — line 127
- `Service.set_torque(self, ids: list[int], enabled: bool)` — line 133
- `Service.write_register(self, sid: int, address: int, value: int)` — line 155
- `Service.restore(self, sid: int, changes: list[tuple[int, int]], cancel: Event)` — line 209
- `Service.control_payload(self, sid: int, position: int, speed: int, acc: int, time_raw: int)` — line 223
- `Service.control(self, ids: list[int], position: int, speed: int, acc: int, time_raw: int, method: str='write', cancel: Event | None=None)` — line 242
- `Service.action(self)` — line 283
- `Service.reset(self, sid: int)` — line 289
- `Service.calibration(self, sid: int)` — line 295
- `Service.pwm(self, kind: str, value: int)` — line 309

## simulator.py

Explicit virtual bus. Never imports serial or opens a /dev device.

### VirtualLink

- `VirtualLink.__init__(self, trace=None)` — line 10
- `VirtualLink.close(self)` — line 55
- `VirtualLink.tick(self)` — line 58
- `VirtualLink.exchange(self, sid, ins, params=b'', expected=0, wait=True)` — line 84

## ui/__init__.py

Public desktop entry points.

## ui/app.py

Application bootstrap.

- `configure(app: Q.QApplication)` — line 10
- `main(argv=None)` — line 18
## ui/connection.py

Connection workflows and their local state.

### ConnectionController

- `ConnectionController.__init__(self, ui: Window)` — line 22
- `ConnectionController.ports(self)` — line 25
- `ConnectionController.toggle_connection(self)` — line 34
- `ConnectionController.scan(self)` — line 86
- `ConnectionController.add_servo(self, s)` — line 112
- `ConnectionController.scan_progress(self, payload)` — line 130
- `ConnectionController.identify(self)` — line 136
- `ConnectionController.selection_changed(self)` — line 157
- `ConnectionController.activate_selection(self)` — line 177

## ui/diagnostics.py

Diagnostics workflows and their local state.

### DiagnosticsController

- `DiagnosticsController.__init__(self, ui: Window)` — line 20
- `DiagnosticsController.toggle_test(self)` — line 26
- `DiagnosticsController.clear_test(self)` — line 32
- `DiagnosticsController.test_tick(self)` — line 36
- `DiagnosticsController.open_firmware(self)` — line 69

## ui/monitoring.py

Monitoring workflows and their local state.

### MonitoringController

- `MonitoringController.__init__(self, ui: Window)` — line 19
- `MonitoringController.show_feedback(self, result)` — line 26
- `MonitoringController.series_toggle(self, key, checked)` — line 53
- `MonitoringController.plot_config(self)` — line 60
- `MonitoringController.capture_toggle(self)` — line 66
- `MonitoringController.capture_finish(self)` — line 91
- `MonitoringController.save_capture(self)` — line 103
- `MonitoringController.clear_data(self)` — line 114

## ui/motion.py

Motion workflows and their local state.

### MotionController

- `MotionController.__init__(self, ui: Window)` — line 18
- `MotionController.goal_changed(self, value)` — line 26
- `MotionController.slider_changed(self, value)` — line 31
- `MotionController.slider_release(self)` — line 36
- `MotionController.send(self)` — line 39
- `MotionController.dispatch_control(self, args: MotionArgs)` — line 54
- `MotionController.action(self)` — line 63
- `MotionController.torque_change(self, checked)` — line 80
- `MotionController.torque_done(self, ids, enabled)` — line 94
- `MotionController.stop_all(self)` — line 100
- `MotionController.torque_off(self, ids)` — line 124
- `MotionController.begin_auto(self, step)` — line 141
- `MotionController.cancel_auto(self, silent=False)` — line 172
- `MotionController.auto_tick(self)` — line 178

## ui/programming.py

Programming workflows and their local state.

### ProgrammingController

- `ProgrammingController.__init__(self, ui: Window)` — line 19
- `ProgrammingController.read_memory(self)` — line 22
- `ProgrammingController.describe_register(self)` — line 34
- `ProgrammingController.show_memory(self, result)` — line 48
- `ProgrammingController.save_parameter(self)` — line 98
- `ProgrammingController.save_image(self)` — line 155
- `ProgrammingController.load_image(self)` — line 183
- `ProgrammingController.recovery(self)` — line 287
- `ProgrammingController.calibrate(self)` — line 314

## ui/pwm.py

Pwm workflows and their local state.

### PwmController

- `PwmController.__init__(self, ui: Window)` — line 15
- `PwmController.pwm_slide(self, value)` — line 18
- `PwmController.pwm_command(self, kind, value)` — line 24
- `PwmController.begin_pwm_auto(self, step)` — line 41

## ui/signals.py

Explicit Qt clicked(bool) boundary; no callable-signature inspection.

### ClickAction

- `ClickAction.__init__(self, button: QAbstractButton, callback: Callable[[], object])` — line 13
- `ClickAction.trigger(self, checked: bool)` — line 19

- `bind_click(button: QAbstractButton, callback: Callable[[], object], on_error: Callable[[str], None] | None=None)` — line 27
## ui/state.py

Typed state owned by the motion and monitoring features.

### ServoCommand


### PwmPulse


### AutoBase


### ServoAuto


### PwmAuto


### CaptureState


## ui/trend.py

Telemetry plot rendering without device I/O.

### Trend

- `Trend.__init__(self)` — line 23
- `Trend.ranges(self)` — line 34
- `Trend.paintEvent(self, event)` — line 49

## ui/view.py

Widget layout. Device operations live in feature controllers.

### DesktopView

- `DesktopView.note(self, text: str)` — line 37
- `DesktopView.bind_action(self, button: Q.QAbstractButton, callback: Callable[[], object])` — line 40
- `DesktopView.build_ui(self, demo: bool=False)` — line 43
- `DesktopView.spin(lo: int, hi: int, value: int)` — line 139
- `DesktopView.button(self, text: str, fn: Callable[[], object], kind: str='device')` — line 145
- `DesktopView.tab(self, title: str)` — line 154
- `DesktopView.build_debug(self)` — line 165
- `DesktopView.build_programming(self)` — line 305
- `DesktopView.build_upgrade(self)` — line 338
- `DesktopView.build_pwm(self)` — line 370
- `DesktopView.build_log(self)` — line 440

## ui/widgets.py

Checked access to widgets created by the desktop layout.

- `required(value: T | None)` — line 8
## ui/window.py

Desktop composition and cross-feature coordination.

### Window

- `Window.__init__(self, demo: bool=False)` — line 25
- `Window.note(self, text)` — line 59
- `Window.notice(self, text)` — line 64
- `Window.trace(self, kind, raw)` — line 67
- `Window.ids(self)` — line 71
- `Window.update_controls(self)` — line 74
- `Window.job_failed(self, name, error)` — line 155
- `Window.finish_job(self)` — line 174
- `Window.tab_changed(self, index)` — line 186
- `Window.tick(self)` — line 196
- `Window.closeEvent(self, event)` — line 298

## wire.py

Bounded, resynchronizing byte transport. All callers are serialized by the controller.

### LinkError


### Timeout


### StatusError

- `StatusError.__init__(self, bits: int)` — line 21

- `frame(sid: int, instruction: int, parameters: bytes=b'')` — line 30
### Parser

- `Parser.__init__(self)` — line 38
- `Parser.feed(self, data: bytes)` — line 41

### SerialLink

- `SerialLink.__init__(self, path: str, baud: int=1000000, parity: str='N', timeout_ms: int=50, trace: Trace | None=None)` — line 69
- `SerialLink.baud(self)` — line 97
- `SerialLink.baud(self, value: int)` — line 101
- `SerialLink.close(self)` — line 104
- `SerialLink.exchange(self, sid: int, ins: int, params: bytes=b'', expected: int=0, wait: bool=True)` — line 107

### Bus

- `Bus.__init__(self, link: Link)` — line 138
- `Bus.read(self, sid: int, address: int, length: int)` — line 141
- `Bus.send(self, sid: int, address: int, data: bytes, registered: bool=False)` — line 151
- `Bus.sync(self, address: int, entries: list[tuple[int, bytes]])` — line 161
- `Bus.action(self)` — line 173
- `Bus.reset(self, sid: int)` — line 176

