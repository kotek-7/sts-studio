# モジュール・関数索引

モジュール別のシグネチャと定義行を示します。動作仕様はSPECIFICATION / DESIGNを参照してください。

## __init__.py

STS Studio servo configuration and monitoring application.

## __main__.py



## automation.py

Pure scheduling/statistics models; no I/O and no sleeping inside the UI thread.

### Pattern

- `Pattern.__init__(self, start, end, step=None, clamp=True)` — line 6
- `Pattern.next(self)` — line 10

### CommunicationStats

- `CommunicationStats.add(self, seconds, bytes_count, kind='success')` — line 32
- `CommunicationStats.report(self)` — line 38

## catalog.py

Register definitions, model identification, and value encoding.

- `unsigned_word(value, order='little', sign_bit=-1)` — line 9
- `decode(data, order='little', sign_bit=-1)` — line 15
### Register

- `Register.from_dict(cls, d)` — line 23
- `Register.writable(self)` — line 25
- `Register.limits(self)` — line 27
- `Register.pack(self, value, order)` — line 32
- `Register.unpack(self, raw, order)` — line 37

### Profile

- `Profile.__init__(self, data)` — line 40
- `Profile.decode_memory(self, data, base=0)` — line 48
- `Profile.field(self, a)` — line 50

- `identify(header)` — line 54
## files.py

Strict, non-executing file formats. Xdat support is limited to STS parameter blocks.

### ParameterImage

- `ParameterImage.load(cls, path)` — line 10
- `ParameterImage.save(self, path)` — line 16
- `ParameterImage.changes(self, servo, current)` — line 19

- `csv_row(row, index, legacy)` — line 32
- `write_csv(path, rows, legacy=False)` — line 36
### Recorder

- `Recorder.__init__(self, path, legacy=False)` — line 43
- `Recorder.append(self, row)` — line 46
- `Recorder.flush(self)` — line 47

- `inspect_firmware(path)` — line 54
## jobs.py

One bounded serial worker. UI keeps no backlog of movement requests.

### Worker

- `Worker.__init__(self)` — line 10
- `Worker.submit(self, token, function)` — line 13
- `Worker.run(self)` — line 16
- `Worker.close(self)` — line 23

## service.py

Servo operations. No Qt dependencies; effects and partial failures are explicit.

### Servo

- `Servo.firmware(self)` — line 11

### Service

- `Service.__init__(self, link)` — line 14
- `Service.discover(self, sid)` — line 15
- `Service.scan(self, start, end, cancel, progress)` — line 20
- `Service.get(self, sid)` — line 27
- `Service.snapshot(self, sid)` — line 31
- `Service.feedback(self, sid)` — line 38
- `Service.read_value(self, sid, address)` — line 43
- `Service.verify(self, sid, address, data, ignore_alarm=False)` — line 47
- `Service.write_verified(self, sid, address, data, ignore_alarm=False)` — line 51
- `Service.set_torque(self, ids, enabled)` — line 53
- `Service.write_register(self, sid, address, value)` — line 66
- `Service.restore(self, sid, changes, cancel)` — line 93
- `Service.control_payload(self, sid, position, speed, acc, time_raw)` — line 100
- `Service.control(self, ids, position, speed, acc, time_raw, method='write', cancel=None)` — line 107
- `Service.action(self)` — line 123
- `Service.reset(self, sid)` — line 128
- `Service.calibration(self, sid)` — line 131
- `Service.pwm(self, kind, value)` — line 140

## simulator.py

Explicit virtual bus. Never imports serial or opens a /dev device.

### VirtualLink

- `VirtualLink.__init__(self, trace=None)` — line 7
- `VirtualLink.close(self)` — line 15
- `VirtualLink.tick(self)` — line 16
- `VirtualLink.exchange(self, sid, ins, params=b'', expected=0, wait=True)` — line 28

## ui.py

Qt interface for servo control, configuration, diagnostics, and PWM.

- `after_monitor(fn)` — line 19
### Trend

- `Trend.__init__(self)` — line 33
- `Trend.ranges(self)` — line 36
- `Trend.paintEvent(self, event)` — line 42

### Window

- `Window.__init__(self, demo=False)` — line 65
- `Window.spin(lo, hi, value)` — line 95
- `Window.button(self, text, fn, kind='device')` — line 97
- `Window.tab(self, title)` — line 102
- `Window.build_debug(self)` — line 104
- `Window.build_programming(self)` — line 131
- `Window.build_upgrade(self)` — line 139
- `Window.build_pwm(self)` — line 144
- `Window.build_log(self)` — line 160
- `Window.note(self, text)` — line 163
- `Window.notice(self, text)` — line 166
- `Window.trace(self, kind, raw)` — line 167
- `Window.ids(self)` — line 169
- `Window.update_controls(self)` — line 170
- `Window.submit(self, name, fn, done=None, quiet=False)` — line 183
- `Window.job_done(self, token, result)` — line 186
- `Window.job_failed(self, token, error)` — line 193
- `Window.finish_job(self)` — line 205
- `Window.ports(self)` — line 210
- `Window.toggle_connection(self)` — line 216
- `Window.scan(self)` — line 227
- `Window.add_servo(self, s)` — line 234
- `Window.scan_progress(self, payload)` — line 240
- `Window.identify(self)` — line 244
- `Window.selection_changed(self)` — line 250
- `Window.read_memory(self)` — line 256
- `Window.activate_selection(self)` — line 258
- `Window.describe_register(self)` — line 267
- `Window.show_memory(self, result)` — line 272
- `Window.show_feedback(self, result)` — line 291
- `Window.tab_changed(self, index)` — line 300
- `Window.tick(self)` — line 304
- `Window.goal_changed(self, value)` — line 334
- `Window.slider_changed(self, value)` — line 336
- `Window.slider_release(self)` — line 339
- `Window.pwm_slide(self, value)` — line 341
- `Window.send(self)` — line 345
- `Window.dispatch_control(self, args)` — line 350
- `Window.action(self)` — line 355
- `Window.torque_change(self, checked)` — line 358
- `Window.torque_done(self, ids, enabled)` — line 363
- `Window.stop_all(self)` — line 366
- `Window.torque_off(self, ids)` — line 375
- `Window.begin_auto(self, step)` — line 382
- `Window.cancel_auto(self, silent=False)` — line 389
- `Window.auto_tick(self)` — line 392
- `Window.series_toggle(self, key, checked)` — line 399
- `Window.plot_config(self)` — line 403
- `Window.capture_toggle(self)` — line 405
- `Window.capture_finish(self)` — line 412
- `Window.save_capture(self)` — line 417
- `Window.clear_data(self)` — line 422
- `Window.save_parameter(self)` — line 426
- `Window.save_image(self)` — line 446
- `Window.load_image(self)` — line 453
- `Window.recovery(self)` — line 481
- `Window.calibrate(self)` — line 488
- `Window.toggle_test(self)` — line 490
- `Window.clear_test(self)` — line 492
- `Window.test_tick(self)` — line 493
- `Window.open_firmware(self)` — line 503
- `Window.pwm_command(self, kind, value)` — line 509
- `Window.begin_pwm_auto(self, step)` — line 515
- `Window.closeEvent(self, event)` — line 519

- `main(argv=None)` — line 529
## wire.py

Bounded, resynchronizing byte transport. All callers are serialized by the controller.

### LinkError


### Timeout


### StatusError

- `StatusError.__init__(self, bits)` — line 9

- `frame(sid, instruction, parameters=b'')` — line 14
### Parser

- `Parser.__init__(self)` — line 20
- `Parser.feed(self, data)` — line 21

### SerialLink

- `SerialLink.__init__(self, path, baud=1000000, parity='N', timeout_ms=50, trace=None)` — line 37
- `SerialLink.baud(self)` — line 43
- `SerialLink.baud(self, value)` — line 45
- `SerialLink.close(self)` — line 46
- `SerialLink.exchange(self, sid, ins, params=b'', expected=0, wait=True)` — line 47

### Bus

- `Bus.__init__(self, link)` — line 66
- `Bus.read(self, sid, address, length)` — line 67
- `Bus.send(self, sid, address, data, registered=False)` — line 70
- `Bus.sync(self, address, entries)` — line 73
- `Bus.action(self)` — line 79
- `Bus.reset(self, sid)` — line 80

