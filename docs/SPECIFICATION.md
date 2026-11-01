# STS Studio 機能仕様書

機能ごとの入力、実行手順、成功条件、エラー処理を定義します。機械可読定義は `spec/features.json`、設計は [DESIGN.md](DESIGN.md)、メモリ表は [REGISTERS.md](REGISTERS.md) を参照してください。

検証範囲は [VALIDATION.md](VALIDATION.md) に記載しています。

## CON-01: シリアル接続

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| port | 既存の /dev/tty* |
| baud | protocol.json port.baud_choices |
| parity | N/O/E |
| timeout_ms | 5..5000, default50 |

**前提**: DISCONNECTED。実機/デモを明示選択

**実行手順・通信**: 8 data bits / 1 stop bit、RTS/DTR false、排他open。初期baud115200。PWMタブで接続した場合はアダプターをPWMモードへ設定

**成功条件・後状態**: CONNECTED。接続設定をロック

**エラー・中止**: open失敗はDISCONNECTEDのまま。権限/占有/切断の例外を表示

**実装**: `wire.SerialLink` / **テスト**: `test_connect_has_no_writes`

## SCAN-01: ID検索

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| first | 0..253 |
| last | first..253 |

**前提**: CONNECTED。動作・他I/Oなし

**実行手順・通信**: 指定範囲に253が含まれる場合はID253を先に識別し、残りのIDへREAD address0 length9を昇順送信。Timeoutは未検出として継続

**成功条件・後状態**: 検出一覧更新。手動選択でREADY。検索だけではトルクや設定を書かない

**エラー・中止**: キャンセルは進行中requestの完了/timeout後。破損/切断は停止

**実装**: `service.Service.scan` / **テスト**: `test_scan_read_not_ping`

## READ-01: モデル別メモリ表

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| id | 検出した個別ID |

**前提**: READYかつprofile既知

**実行手順・通信**: 設定タブでEEPROM0..39とRAM40..最終定義アドレスを周期READ。編集中のEdit列を保持して現在値を更新。操作タブの選択時には全メモリを読まない

**成功条件・後状態**: 表に実読取値。default列の値を実機値として使わない

**エラー・中止**: 未知FWは識別情報だけ表示し書込禁止。異常ビットを保持

**実装**: `service.Service.snapshot` / **テスト**: `test_programming_refresh_preserves_edit`

## READ-02: フィードバック

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| id | 選択中ID |
| period_ms | 20..5000, default50 |

**前提**: READY、監視ON、他I/Oなし

**実行手順・通信**: profileのfeedback_start..feedback_endを1回READ。標準STSは56から17byte。Goalは同じ応答のoffset11/12をsign15で復号。statusは応答パケットのERROR

**成功条件・後状態**: 位置/速度/負荷/電流/温度/電圧/移動/状態。電圧はraw/10。他は原則生値。記録にtimestamp/id/errorを付与

**エラー・中止**: timeout時は過去値であることを表示し、設定周期で再試行。設定保存の失敗だけではモニターをOFFにしない

**実装**: `service.Service.feedback` / **テスト**: `test_goal_is_feedback_word_not_target`

## CTRL-01: Write・Set

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| ids | 選択ID集合 |
| acc | 0..254 |
| goal | -32766..32766 |
| speed | -32766..32766 |
| time_raw | 0..65535 |

**前提**: READY、profile.motion_supported、明示的な送信操作

**実行手順・通信**: profile.control_startへ7byte: acc,u16(goal sign15),u16(time raw),u16(speed sign15)。Write命令3。SCSはbig endianで非負goal/speed

**成功条件・後状態**: 各対象へ指令を送信。到達・実行完了を意味しない。確認用の追加READは送らない

**エラー・中止**: 一部失敗は停止・エラー。再送しない。Timeのモード依存解釈は推測しない

**実装**: `service.Service.control` / **テスト**: `test_write_vector`

## CTRL-02: Sync Write

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| ids | 重複なし1..30台 |
| payload | CTRL-01と同じ |

**前提**: READY。全台のpayloadを送信前検証

**実行手順・通信**: ID254 instruction131、共通control_start、width7、各(id,payload)。250byte以内の1フレーム

**成功条件・後状態**: 1フレームの同期指令を送信。実行・到達完了を保証しない。追加READなし

**エラー・中止**: 異なる制御アドレスの混在、30台超、重複、不正payloadは送信前拒否

**実装**: `service.Service.control` / **テスト**: `test_sync_vector`

## CTRL-03: Reg Write

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| ids | 選択ID集合 |
| payload | CTRL-01と同じ |

**前提**: READY

**実行手順・通信**: 各IDへinstruction4を送信しpending集合を更新。追加READなし

**成功条件・後状態**: 登録のみ。明示Actionまで実行しない

**エラー・中止**: 登録途中の失敗でpendingを捨てない。Actionは同じバス上の他ソフトの登録にも作用する

**実装**: `service.Service.control` / **テスト**: `test_registered_not_executed`

## CTRL-04: Action

状態: **対応**

### 入力

追加入力なし。

**前提**: 接続中、明示的な実行操作

**実行手順・通信**: ID254 instruction5で一斉実行を要求。追加READなし

**成功条件・後状態**: 送信後にローカルpendingを解除。実機の実行完了確認ではない

**エラー・中止**: 送信失敗時はpending保持。自動再送なし

**実装**: `service.Service.action` / **テスト**: `test_action_broadcast`

## CTRL-05: Torque Enable / OFF

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| ids | 選択ID集合 |
| enabled | 0/1 |

**前提**: profile既知

**実行手順・通信**: address40へ0または1を書き込み、読み戻しで確認。ONでは目標位置を書き換えない

**成功条件・後状態**: ON/OFF確認済みIDを報告。STOPは自動動作と待機中の手動指令を破棄してOFFを送る。監視ONならFB・記録を継続。PWM中は出力OFFも送信

**エラー・中止**: OFF通信失敗は停止未確認と表示。ソフト停止は物理非常停止ではない

**実装**: `service.Service.set_torque` / **テスト**: `test_stop_keeps_feedback_and_recording`

## CTRL-06: 目標スライダー

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| value | 選択profileの位置範囲、STS初期0..4095 |
| live | 初期ON |

**前提**: READY

**実行手順・通信**: Live ONではスライダー値の変更時に送信。I/O中は最新の値1件だけを保持し、古い指令を蓄積しない

**成功条件・後状態**: Live OFFでは入力欄のみ更新。STOPで待機中の指令を破棄

**エラー・中止**: 忙しい間の変更は送信しない。旧指令をキューに蓄積しない

**実装**: `ui.motion.MotionController.slider_changed` / **テスト**: `test_live_slider_and_stop_discards_waiting_target`

## AUTO-01: Sweep往復

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| start | 目標範囲 |
| end | 目標範囲 |
| delay_ms | 10..600000 |

**前提**: READY、対象IDとwrite方式固定。RegWriteは禁止

**実行手順・通信**: start,endを交互送信。通信完了後にdelayを待つ。通常モニターと独立した締切で動作する

**成功条件・後状態**: 停止で次の予約を破棄。最終トルク状態は維持

**エラー・中止**: I/O失敗は自動動作停止。停止は今進行中の1指令を取り消せない

**実装**: `automation.Pattern` / **テスト**: `test_step_timer_is_independent`

## AUTO-02: Step往復

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| start | 目標範囲 |
| end | 目標範囲 |
| step | 1..32766 |
| delay_ms | 10..600000 |

**前提**: AUTO-01同様

**実行手順・通信**: 最初にstartからstepを加減した値を送信。端点を跨いだ時に向きを反転する。端点を超える1回の指令を含む

**成功条件・後状態**: 例:1000..1100/step30は1030,1060,1090,1120,1090,1060,1030,1000…

**エラー・中止**: step0、start=endは開始前拒否

**実装**: `automation.Pattern` / **テスト**: `test_step_observed_sequence`

## PLOT-01: 複数系列・範囲・ズーム

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| series | position/goal/load/speed/current/temperature/voltage |
| window_s | 1..600 |
| offset_s | 0..600 |
| lower_upper | 任意有限値 lower<upper またはauto |

**前提**: 取得サンプルがある

**実行手順・通信**: 位置とGoalは左軸0..4096/position_divisor、その他は右軸±1000。速度はspeed_multiplierを適用。左右の軸を表示。範囲・横窓を変更できる

**成功条件・後状態**: 表示変更は通信を発生しない。単位は凡例/表記通り

**エラー・中止**: 空データは空グラフ。不正な縦範囲はautoへ

**実装**: `ui.Trend` / **テスト**: `test_plot_bounds`

## DATA-01: 周期保存記録・Export・Empty

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| flush_interval_seconds | 1..86400 |
| path | 利用者選択 |
| format | CSV / TXT |

**前提**: READY、監視ON。記録開始を明示

**実行手順・通信**: 既定はrecord.txt。CSVも選択可能。最大100000件保持。指定間隔で追記し停止時にflush。TXT headerはNo,Pos,Gol,Ft,V,C,T,Vol、1始まり連番と末尾END、CRLF。GolはFB内のGoal値

**成功条件・後状態**: 取得件数を表示。Emptyは記録サンプルとグラフをクリア

**エラー・中止**: 書込失敗時はサンプルを保持し再保存可能。100000件に達すると記録を停止

**実装**: `files.Recorder` / **テスト**: `test_csv_columns`

## PARAM-01: 単一パラメータ保存

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| address | catalog rw行 |
| value | catalog limits（-1/-1は格納幅から導出） |

**前提**: READY、変更値が明示入力。EEPROMならトルクOFF

**実行手順・通信**: 符号・エンディアン変換。EEPROMはlock読取→0→値→readback→元lock。失敗でも元lock復元を試す

**成功条件・後状態**: 確定値を再読込し、lockを操作前の値へ復元

**エラー・中止**: 読取専用・未知profile・型範囲不正は送信前拒否。復元失敗を隠さない

**実装**: `service.Service.write_register` / **テスト**: `test_parameter_lock_finally`

## PARAM-02: ID・通信速度変更

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| id | 0..253 |
| baud_code | STS 0..7 |

**前提**: PARAM-01条件。同じバスに重複ID応答なし

**実行手順・通信**: ID変更後は新ID、速度変更後は対応baudへ追従しreadback。復元先も追従

**成功条件・後状態**: 選択一覧/表示を更新。別系列のbaud codeは不明として禁止

**エラー・中止**: 応答消失時は変更成否不明、新接続値を表示。成功扱いしない

**実装**: `service.Service.write_register` / **テスト**: `test_id_baud_tracking`

## FILE-01: Save xdat

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| path | *.xdat |

**前提**: READY、STS profile、設定を新規読取

**実行手順・通信**: [start:u8=0][count:u8=40][memory0..39][trailer:2 bytes=0000]、計44byte

**成功条件・後状態**: 末尾2byteは読込・再保存時に保持

**エラー・中止**: STS以外は未対応として拒否。ファイル書込失敗を表示

**実装**: `files.ParameterImage` / **テスト**: `test_xdat_roundtrip`

## FILE-02: Load・差分プレビュー

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| path | STS *.xdat |

**前提**: READY。モデルbytes3/4とFWbytes0/1一致

**実行手順・通信**: 長さ/addressを検証し差分だけ一覧化。選択行をアドレス順適用、ID/baudは末尾。初期ではID/baud選択OFF

**成功条件・後状態**: 読み込みだけでは送信しない。各行verified、適用済みリストを返す

**エラー・中止**: 中断/失敗時に自動rollbackしない。適用済み行と失敗行を報告

**実装**: `service.Service.restore` / **テスト**: `test_restore_partial_failure`

## RESET-01: Recovery

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| id | 単一選択ID |

**前提**: 利用者が確認ダイアログで明示実行

**実行手順・通信**: instruction6を送信

**成功条件・後状態**: 送信済みのみ表示。対象情報を破棄し再検索を要求

**エラー・中止**: 工場設定/ID/baudへの復帰は未実機検証。完了とは表示しない

**実装**: `service.Service.reset` / **テスト**: `test_recovery_wire_only`

## CAL-01: STS中点校正

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| id | 単一STS ID |

**前提**: トルクOFF、異常なし

**実行手順・通信**: address40に128を送信。50ms後positionを読んで2048±2を検査

**成功条件・後状態**: 一致時だけ校正確認済み

**エラー・中止**: 対応FW不明・読戻し不一致は未確認と表示

**実装**: `service.Service.calibration` / **テスト**: `test_calibration_verification`

## TEST-01: 通信テスト

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| id | 選択ID |
| mode | 成功時連続、timeout時50ms待機 |

**前提**: READY、他自動動作なし

**実行手順・通信**: モニター周期とは独立してfeedback READを連続実行。各要求の応答時間、試行/成功/timeout、min/mean/max、実TX+RX量/経過時間を集計。GUIには各要求完了時に反映

**成功条件・後状態**: 停止で集計保持。Clearで統計と表示をクリア

**エラー・中止**: timeoutを成功時間へ混ぜない。リンク例外で停止。速度は実効値でbaud推定ではない

**実装**: `automation.CommunicationStats` / **テスト**: `test_fast_test_ignores_monitor_period`

## PWM-01: アダプターPWM手動

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| pulse_us | 500..2500 |
| enabled | 0/1 |

**前提**: 接続中。対応アダプターID253への操作を利用者が明示選択

**実行手順・通信**: PWMタブでID253 address9=0、他タブで9=1。パルスはaddress33 u16LE、enableはaddress35 u8。スライダーとプリセットに対応

**成功条件・後状態**: 送信済み（出力未確認）と表示。サーボID253とは別のadapter制御として区別

**エラー・中止**: 実機アダプターでの出力は未検証。モード切替をタブ表示だけで自動送信しない

**実装**: `service.Service.pwm` / **テスト**: `test_tab_mode_switch_and_pwm_stop`

## PWM-02: PWM自動往復・ステップ

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| min_us | 500..2500 |
| max_us | min..2500 |
| delay_ms | 10..600000 |
| step_us | 1..2000 |

**前提**: PWM-01条件

**実行手順・通信**: AUTOのスケジューラからpulse指令。min/maxはソフトウェア側の出力範囲制限

**成功条件・後状態**: 停止で予約解除。明示OFFで出力停止指令

**エラー・中止**: Min/Maxはソフトウェアの出力範囲。アダプターへの永続設定には未対応

**実装**: `automation.Pattern` / **テスト**: `test_pwm_pattern_bounds`

## FW-01: ファームウェアを開く・検査

状態: **対応**

### 入力

| 項目 | 型・範囲・既定値 |
|---|---|
| path | hex/bin/fbin/mbin/xbin |

**前提**: ローカルファイルを明示選択

**実行手順・通信**: サイズ/SHA256を表示。Intel HEXの長さ・checksum・record型・EOF・重複addressを検査

**成功条件・後状態**: 検査結果のみ。ファイル内容を実行しない

**エラー・中止**: 不正HEXは拒否。暗号化/機種適合性は判定不可

**実装**: `files.inspect_firmware` / **テスト**: `test_hex_validation`

## FW-02: Upgrade送信

状態: **未対応**

### 入力

追加入力なし。

**前提**: 対象機器の更新方式への対応が必要

**実行手順・通信**: ファイル検査画面に書き込み未対応と表示

**成功条件・後状態**: 送信を開始しない

**エラー・中止**: このバージョンではファームウェア転送に未対応

**実装**: `—` / **テスト**: `—`

## PROF-01: SCS/SMS/STSプロファイル

状態: **対応**

### 入力

追加入力なし。

**前提**: ヘッダがcatalogのFW範囲に一致

**実行手順・通信**: 10個のDebug属性と6個の設定メモリ表を独立管理。設定表なしでもDebug属性があれば監視可能。torque_address=0のプロファイルは動作を許可しない。設定メモリ未定義ならProgramming書込禁止

**成功条件・後状態**: 型番の推測をせず不明はUnknown表記

**エラー・中止**: SCS/SMSは静的定義・シミュレータのみ検証。物理互換は未確認

**実装**: `catalog.identify` / **テスト**: `test_debug_profiles_without_memory_table`

## MODBUS-01: Modbus/PWM専用サーボFWプロファイル

状態: **未対応**

### 入力

追加入力なし。

**前提**: 対象プロトコル仕様と対応機器が必要

**実行手順・通信**: 通信バックエンドはSCSバスに対応。Modbus通信は提供しない

**成功条件・後状態**: 未対応として明示

**エラー・中止**: 本版の通信バックエンドはSCSバスのみ

**実装**: `—` / **テスト**: `—`

## PWM-03: Signal Min/Maxのアダプター設定

状態: **未対応**

### 入力

追加入力なし。

**前提**: 対応アダプターが必要

**実行手順・通信**: ソフトウェア側の出力範囲を設定。アダプターへの保存は未対応

**成功条件・後状態**: アダプターの永続設定は変更しない

**エラー・中止**: 永続設定ができたとは表示しない

**実装**: `—` / **テスト**: `—`

## 通信フレームの検証ベクトル

| ID | TX | 意味 |
|---|---|---|
| search | `ff ff 01 04 02 00 09 ef` | Read ID1 address0 length9 for identification |
| feedback | `ff ff 01 04 02 38 11 af` | Read ID1 address56 length17 |
| write | `ff ff 01 0a 03 29 11 d2 04 c8 01 41 01 d6` | ID1 address41: acceleration17, position1234, time456, speed321 |
| sync | `ff ff fe 0c 83 29 07 01 11 d2 04 c8 01 41 01 4f` | Broadcast sync write address41 width7, ID1 same payload |
| registered | `ff ff 01 0a 04 29 11 d2 04 c8 01 41 01 d5` | Registered write, no immediate motion |
| action | `ff ff fe 02 05 fa` | Broadcast execute registered writes |
| unlock | `ff ff 01 04 03 37 00 c0` | EEPROM unlock |
| parameter | `ff ff 01 04 03 15 37 ab` | Position P=55 |
| lock | `ff ff 01 04 03 37 01 bf` | EEPROM lock |
| reset | `ff ff 01 02 06 f6` | Reset request; completion and resulting communication settings require device verification |
| pwm_mode | `ff ff fd 04 03 09 00 f2` | PWM adapter ID253, address9=0: PWM mode |
| bus_mode | `ff ff fd 04 03 09 01 f1` | PWM adapter ID253, address9=1: bus mode |
| pwm_pulse | `ff ff fd 05 03 21 dc 05 f8` | PWM adapter address33, 1500us little endian |
| pwm_on | `ff ff fd 04 03 23 01 d7` | PWM adapter address35=1 |
| pwm_off | `ff ff fd 04 03 23 00 d8` | PWM adapter address35=0 |
