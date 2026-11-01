# 設計・実装契約

この文書は再実装可能な設計契約です。画面の見た目だけでなく、入力から通信、状態更新、永続化までを定義します。個々の機能契約は `spec/features.json`、数値とバイト配置は `spec/catalog.json` / `spec/protocol.json` を正本とします。

## 1. 対象環境と構成

Ubuntu上で動作するQtアプリケーションです。USBシリアルを介してFEETECH SCSバスへ接続します。STS用の動作・設定・監視機能を中心とし、機種とファームウェアの組み合わせからメモリ表を選択します。Python 3.10以上、PyQt5、pyserialを使用します。

デモモードでは仮想サーボID1/2を使用し、物理ポートを開きません。通信・ファイル・GUIを自動テストしています。実機での電気的挙動、電源断後の設定保持、PWM波形は未検証です。

## 2. コンポーネントとデータ所有権

| モジュール | 入力 | 出力・所有する状態 | 外部副作用 |
|---|---|---|---|
| catalog | 3つの仕様JSON | immutable Register、Profile、モデル解決 | JSON読取のみ |
| wire.Parser | 断片bytes | チェックサム確認済みフレーム列、残余buffer | なし |
| wire.SerialLink | port/baud/parity/timeout、request | RX payload/error、tx/rx byte counters | pyserial 8N/O/E1 |
| wire.Bus | ID/address/data | read/write/sync/action/reset | SerialLinkへ委譲 |
| service.Service | 操作要求 | discovered Servo辞書、pending ID集合 | Busへ委譲 |
| files | Path / memory / rows | xdat、CSV、HEX検査結果 | 明示選択ファイルの読書き |
| automation | start/end/step、応答時間 | 次目標値、統計 | なし |
| jobs.Worker | (token, function) | done/failed/progress/trace signals | 1本の直列実行thread |
| ui.Window | UI操作とsignal | 選択ID、キャッシュ、グラフ、録画状態 | workerへ要求、明示file dialog |
| simulator.VirtualLink | 同じexchangeインターフェース | 仮想ID1/2とアダプター | 物理ポートへのアクセスなし |

`Servo` = {sid:int, model:str, profile:Profile|None, header:bytes[9]}。firmware表示はheader[0].header[1]、モデル識別はheader[3]/header[4]。header[5]を検索IDに上書きして真のIDと決めつけません。

`Snapshot` = {id:int, raw:bytes, values:dict[address,int], error:int}。
`Feedback` = {id:int, values:dict[address,int], error:int, timestamp:Unix seconds}。
`TelemetryRow` はFeedback.valuesにid,timestamp,error,goalを加えます。整数キーはレジスタアドレス、文字列キーはメタデータです。

## 3. 接続・状態遷移

- **DISCONNECTED**: serviceなし。ポート選択、更新、通信条件、デモ切替だけ可能。ファイル検査と仕様閲覧は常に可能。
- **CONNECTED**: portは開いているが、既知profileのサーボ未選択。検索、ID指定、アダプター操作が可能。
- **READY**: 選択IDとprofileが存在。単一の操作を開始できる。複数選択時、表示・設定の対象は選択IDを昇順にした先頭。動作指令の対象は選択集合全体。
- **BUSY**: 1個のI/Oジョブが実行中。接続条件、対象選択、追加動作を無効にする。モニターのtickは捨て、未送信動作を蓄積しない。
- **AUTO**: Sweep/Stepの対象ID、速度、加速度、Time、方式、周期を開始時に固定。UI値を書き換えても走行中の契約を変えない。
- **TESTING**: フィードバックREADを周期的に発行して統計を集計。通常モニターと同時送信しない。
- **停止未確認**は別の集合 `uncertain` として保持する。単にDISCONNECTEDにすれば停止したという扱いにはしない。

更新優先順は、停止要求 → 終了要求 → 自動動作 → 通信試験 → 通常モニターです。I/O中にSTOPを押すと、workerのcancelを立て、対象IDをpending_offへ記録。実行中の1要求が終わった後でトルクOFFを送ります。検索/複数台指令/復元は各要求間でcancelを調べます。シリアルrequestの上限時間は設定timeoutとwrite_timeoutに依存するため、STOPはハードウェア割込みではありません。

終了時は自動動作とモニターを停止。実行中ジョブがあれば待ち、続いてcloseを再試行します。ON指令、停止未確認、登録指令が残る場合はUIで明示確認。終了をキャンセルした場合はウィンドウを残します。物理切断時に「停止済み」と表示しません。

## 4. バイトレベル通信

フレーム長は `LEN + 4`。LENはinstruction/errorとchecksumの2byteを含みます。checksumはIDから最後のparameterまでの和を反転して下位8bitを取ります。合法IDは個別0..253、broadcast254。255はIDに使いません。

READ parameters = address:u8,length:u8。status = FF FF ID LEN ERROR DATA... CHECKSUM。
WRITE / REG_WRITE parameters = address:u8,data...。
SYNC_WRITE parameters = address:u8,width:u8,(id:u8,data[width])*N。
ACTION / RESETはparameterなし。

送信前に受信バッファをclearし、全バイトwrite/flush後にdeadlineまで受信します。分割受信を許容し、header以前のnoiseを除去。ID・LENの不正とchecksum違反は再同期。別ID、payload長違い、送信packetそのもののechoは成功として受理しません。status ERRORが立ってpayloadを返さない場合はStatusError。正しい長さのreadでERRORが立つ場合はdataとerrorを両方返し、異常時の測定値を失わない設計です。

動作指令Write/Sync/Reg/Actionは送信のみで、確認用READを追加しません。パラメータ保存とトルク操作はREADで確認します。readback一致はRAM上の値確認であり、電源断後の保持確認ではありません。

## 5. メモリ表の解釈

実行時に使うのはcatalog.jsonであり、表のアドレスをUIとサービスで二重定義しません。`r`は読取専用、`rw`は書込可能、`d`は表示専用属性として扱い書込を許可しません。

2byte値はprofileのendianに従います。方向bitが設定されている値は二の補数ではなくsign-magnitudeです。正値の有効bitはsign_bitより下、負値はabs(value) | (1 << sign_bit)。受信側も下位bitを絶対値に使います。

範囲が`-1,-1`の組なら「入力範囲指定なし」と解釈します。-1を既定の最小最大として使用しません。格納幅と符号bitから有効範囲を導出します。明示範囲がある場合でも符号の表現可能範囲との共通部分だけを受理します。例: sign bit10なのに±32766とする定義は実効±1023に制約します。宣言範囲はcatalogに保持します。

STSの位置オフセットaddress31は符号bit11を使用します。波形・メモリ表の電流はraw値表示で、機種をまたいで6.5mAなどの換算を断定しません。

未知FWは既知STS表へ勝手にフォールバックしません。`model`がSTS3215でもfirmware範囲が不一致ならprofile=Noneで書き込み禁止です。

## 6. 書き込み・復元のトランザクション

通常RAM書き込みは、型・範囲・rwを検証 → WRITE → READ一致確認。トルクOFFだけは戻り値に異常bitがあっても、40=0が確認できればOFF確認済みとして扱います。トルクONや他書込では異常bitを失敗にします。

EEPROMは、torque=0確認 → 現在lock読取 → unlock=0を書き戻し確認 → 値送信 →20ms待機 → 必要ならID/baud追従 → READ一致確認 → finallyで旧lockへ復元。値書込の例外とlock復元の例外は両方報告します。元lockが0なら0へ戻します。

ID変更前は新IDへREAD0/9し、応答があれば拒否。timeoutは空き候補であり、電源OFFや同じIDの衝突まで検出する保証ではありません。値書込後の応答がない場合、変更の有無が不明でも新ID/baudを画面に表示し、成功とは扱いません。STS以外のbaud code変更は対応表未確定のため無効です。

ファイル復元はモデル/FW一致をチェックし、元の値と異なるrw EEPROM行のみを提示します。チェックした行だけを個別に確定し、ID/baudは最後へ送ります。途中失敗で既に確定したEEPROMを自動rollbackしません。適用済みaddress、失敗address、中断状態を報告します。

## 7. 動作・同期・自動運転

STSのcontrolはaddress41から7byteです。accは1byte、goalはsign15/u16、Timeはu16生値、speedはsign15/u16。Timeを「秒」へ換算しません。動作モードごとのTime意味は機種依存であり、raw値をそのまま送信します。

Writeは対象順に送信。Syncは入力と制御アドレスの一致を先に検証し、最大30台を1フレームで送信。Regは対象ごとに登録します。いずれも追加READは行いません。登録途中で1台失敗してもpending IDを消さず、後でActionが影響し得ることを保持します。ACTIONはbroadcastであり、他ソフトが同一バスへ置いた登録指令まで実行する可能性があります。

自動動作は位置到達を待ちません。送信が完了した時刻からdelay_ms後に次の1指令を発行します。SweepはStart→Endを反復。Stepは最初にstartからstepを加減して送信し、端点を跨いだ時点で折り返します。1000..1100/step30は1030,1060,1090,1120,1090…となります。PWMの自動範囲は端点でclampします。

自動動作停止だけではトルクを変更しません。STOPは全選択IDと過去に操作したIDの和集合へOFFを試します。1台失敗しても他のOFFを試し、未確認IDを明示します。

## 8. ファイル形式

### STS xdat

設定ファイルは44byte: start=0, count=40, memory[0:40], trailer[2]。trailerの意味は未解明です。読込・再保存ではその2byteを保持し、新規出力は0000を使います。start=0/count=40以外は復元適用を拒否します。モデル/FW byteも読取専用の識別情報として比較し、直接書き戻しません。

設定ファイルの拡張子は `.xdat` です。

### CSV / TXT

通常CSVはtimestamp,id,position_steps,goal_steps,load_raw,speed_steps_s,current_raw,temperature_C,voltage_V,error。電圧だけVへ換算。TXTは `No,Pos,Gol,Ft,V,C,T,Vol` header、1始まりの連番、末尾ENDの9列data、CRLFを使用します。同じ測定値列を使ったバイト単位比較テストを行います。保存間隔は1..86400秒です。停止まで記録し、指定間隔ごとに追記、停止時に残りをflushします。データの欠測を0で隠さないため、通常CSVを推奨します。

### Firmware

bin/fbin/mbin/xbinはサイズとSHA256のみ。HEXは各レコードのcolon、byte count、checksum、type、拡張address、重複領域、EOFを検証します。検証が成功してもそのサーボで使えるとは判定しません。検査後に送信を始めるコードはありません。

## 9. 性能・上限・スレッド

UI threadはwidgetと画面用cacheだけを変更します。シリアルportとServiceの操作は1本のworkerで直列化します。I/O処理内からwidgetを直接変更しません。signalで結果を返し、UIのjob tokenに対応するcallbackだけを実行します。

モニター初期50ms、設定20..5000ms。応答が遅ければ間隔は伸び、未処理pollをキューに積みません。serial read timeoutは5..5000ms、write timeout300ms。最大250byteのフレーム。グラフは最大100000件、記録は100000件到達で保存して停止。通信ログは3000行、通信試験表示は500行に制限します。長時間試験の応答統計は別途集約し、全測定値を必要以上に保持しません。

## 10. 仕様・検証・配布

`spec/features.json` が機能契約、`spec/catalog.json` がレジスタとモデル、`spec/protocol.json` が通信仕様と検証ベクトルを定義します。これらを編集後、`python3 tools/render_spec.py` で文書を生成します。

`PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v` でテストを実行します。契約に対応する実装symbolとテスト名の存在、生成文書との一致、パケット検証、設定・記録ファイルのround-trip、GUI状態遷移を検査します。`python3 tools/package.py` でdebとソースアーカイブを生成します。

## 11. 対応範囲

初期baudは115200。Liveスライダーは初期ONで、値の変更時に送信します。I/O中は最新値1件だけを保持し、STOPで破棄します。Timeは機種依存のraw値です。EEPROM操作後は操作前のlock値へ戻します。未知FWへの書き込みと、モデル/FWの異なる設定ファイルの復元は拒否します。

ファームウェアはファイル検査のみ対応します。ファームウェア転送、Modbus、アダプターMin/Maxの永続設定は未対応です。xdatはSTSのaddress0..39に対応し、他ソフトウェアとの往復読込は未検証です。

Goalはフィードバック応答のoffset11/12（標準STSはaddress67/68）をsign15で復号します。追加READはありません。TXTのGolもこの値です。通常の状態表示は応答パケットのERRORを使用し、メモリaddress65のHardware Error Statusは設定表で別に読めます。

## 12. 周期・タブ・停止の制御

2msのPreciseTimerは処理開始の判定に使用します。モニターの締切は独立して20..5000ms、自動動作は各指令完了から指定delay、通信試験は成功後ただちに次要求へ進みます。単一workerでシリアルI/Oを直列化し、モニター周期が自動動作や試験速度を制限しない構成です。OSとI/Oの遅延により実際の間隔は指定値より長くなる場合があります。

停止要求は待機中の手動指令を消去します。PWM出力OFF、モード切替、サーボトルクOFFを優先し、その後は監視ONを保持して読取・記録を続けます。停止失敗の表示は通常FBが成功しても消去しません。書込失敗や一時的なtimeoutだけでモニターを自動OFFにしません。

Debugではフィードバックブロックを1回READ。Programmingではメモリ全体を周期READし、編集欄と選択行を保持して現在値だけを更新します。設定メモリ表がないプロファイルは設定編集を許可せず、監視へフォールバックします。PWMタブへ移るとアダプターmode0、他タブへ移るとmode1を送ります。タブ変更時は自動動作と通信試験を停止します。

Debug属性とメモリ表は別管理です。メモリ表にないFWでもDebug属性に一致すれば監視を使用できます。torque_addressが0の場合は動作・トルク制御を許可しません。位置の左軸上限は4096/position_divisor、その他の右軸は±1000で、速度系列にspeed_multiplierを適用します。

### 監視中の画面更新

周期監視中も操作欄の有効状態とREADY表示を維持します。監視中の設定保存・切断などはGUIスレッドの待機列に入れ、通信完了後に直列実行します。STOPは待機中の操作を破棄し、停止処理を優先します。設定表は変更のあるセルだけを書き換え、編集中の値を維持します。
