# STS Studio 機能一覧

| ID | 機能 | 状態 | 実装 | テスト |
|---|---|---|---|---|
| CON-01 | シリアル接続 | 対応 | `wire.SerialLink` | `test_connect_has_no_writes` |
| SCAN-01 | ID検索 | 対応 | `service.Service.scan` | `test_scan_read_not_ping` |
| READ-01 | モデル別メモリ表 | 対応 | `service.Service.snapshot` | `test_programming_refresh_preserves_edit` |
| READ-02 | フィードバック | 対応 | `service.Service.feedback` | `test_goal_is_feedback_word_not_target` |
| CTRL-01 | Write・Set | 対応 | `service.Service.control` | `test_write_vector` |
| CTRL-02 | Sync Write | 対応 | `service.Service.control` | `test_sync_vector` |
| CTRL-03 | Reg Write | 対応 | `service.Service.control` | `test_registered_not_executed` |
| CTRL-04 | Action | 対応 | `service.Service.action` | `test_action_broadcast` |
| CTRL-05 | Torque Enable / OFF | 対応 | `service.Service.set_torque` | `test_stop_keeps_feedback_and_recording` |
| CTRL-06 | 目標スライダー | 対応 | `ui.Window.slider_changed` | `test_live_slider_and_stop_discards_waiting_target` |
| AUTO-01 | Sweep往復 | 対応 | `automation.Pattern` | `test_step_timer_is_independent` |
| AUTO-02 | Step往復 | 対応 | `automation.Pattern` | `test_step_observed_sequence` |
| PLOT-01 | 複数系列・範囲・ズーム | 対応 | `ui.Trend` | `test_plot_bounds` |
| DATA-01 | 周期保存記録・Export・Empty | 対応 | `files.Recorder` | `test_csv_columns` |
| PARAM-01 | 単一パラメータ保存 | 対応 | `service.Service.write_register` | `test_parameter_lock_finally` |
| PARAM-02 | ID・通信速度変更 | 対応 | `service.Service.write_register` | `test_id_baud_tracking` |
| FILE-01 | Save xdat | 対応 | `files.ParameterImage` | `test_xdat_roundtrip` |
| FILE-02 | Load・差分プレビュー | 対応 | `service.Service.restore` | `test_restore_partial_failure` |
| RESET-01 | Recovery | 対応 | `service.Service.reset` | `test_recovery_wire_only` |
| CAL-01 | STS中点校正 | 対応 | `service.Service.calibration` | `test_calibration_verification` |
| TEST-01 | 通信テスト | 対応 | `automation.CommunicationStats` | `test_fast_test_ignores_monitor_period` |
| PWM-01 | アダプターPWM手動 | 対応 | `service.Service.pwm` | `test_tab_mode_switch_and_pwm_stop` |
| PWM-02 | PWM自動往復・ステップ | 対応 | `automation.Pattern` | `test_pwm_pattern_bounds` |
| FW-01 | ファームウェアを開く・検査 | 対応 | `files.inspect_firmware` | `test_hex_validation` |
| FW-02 | Upgrade送信 | 未対応 | `—` | `—` |
| PROF-01 | SCS/SMS/STSプロファイル | 対応 | `catalog.identify` | `test_debug_profiles_without_memory_table` |
| MODBUS-01 | Modbus/PWM専用サーボFWプロファイル | 未対応 | `—` | `—` |
| PWM-03 | Signal Min/Maxのアダプター設定 | 未対応 | `—` | `—` |
