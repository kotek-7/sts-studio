# CLIの使い方

Ubuntuのdebでは`sts-studio`、展開版では`cli/`内の実行ファイルを使います。ソースからは、プロジェクトのディレクトリで`uv run --locked python -m sts_studio cli`を実行します。GUIの接続を閉じてから同じポートを開いてください。

```sh
uv run --locked python -m sts_studio cli --help
sts-studio --help
sts-studio --version
```

## 接続と出力

共通オプションはサブコマンドより前に指定します。

| オプション | 意味 |
|---|---|
| `--port /dev/ttyUSB0` | 実機ポート。`/dev/serial/by-id/...` も指定可能 |
| `--demo` | 仮想ID1/2。実機には接続しない |
| `--baud 1000000` | 接続速度。既定115200。サーボの設定と合わせる |
| `--parity N` | N / O / E。既定N |
| `--timeout-ms 50` | 応答待ち。5〜5000ms |
| `--trace` | 送受信HEXを標準エラーへ出力 |

標準出力はJSONです。全メモリ読取の `raw` は16進文字列、`values` のキーはレジスタアドレスの文字列です。watchは1行1サンプルのJSON Linesで、各行を即時flushします。`error` は応答パケットのサーボエラービットであり、値が取得できた場合はエラービット付きでも出力します。

終了コードは成功0、通信・設定・ファイル処理の失敗1、引数エラー2、Ctrl+C中断130です。引数エラーはargparseの説明、実行エラーはJSONを標準エラーへ出力します。stopの部分失敗は標準出力のresultsで各IDの成否を示し、終了コード1になります。

各コマンドは終了時にポートを閉じます。終了・Ctrl+CでトルクOFFや設定の巻戻しは行いません。指令送信とトルクのON/OFFは別操作です。

## ポート・検索・監視

```sh
sts-studio ports
sts-studio --demo scan
sts-studio --port /dev/ttyUSB0 --baud 1000000 scan --first 0 --last 20
sts-studio --port /dev/ttyUSB0 --baud 1000000 info --id 1
sts-studio --port /dev/ttyUSB0 --baud 1000000 feedback --id 1
sts-studio --port /dev/ttyUSB0 --baud 1000000 watch --id 1 --interval-ms 100 --count 50 > feedback.jsonl
```

`watch --count 0`（既定）はCtrl+Cまで継続します。応答が遅ければ指定周期より遅くなります。通信エラー時は終了コード1で終了します。scanで見つからないIDはスキップし、0台でも検索処理が成功していれば終了コード0です。

## パラメータの読取・保存

```sh
# 全メモリ
sts-studio --port /dev/ttyUSB0 --baud 1000000 read --id 1

# アドレス21だけ読む
sts-studio --port /dev/ttyUSB0 --baud 1000000 read --id 1 --address 21

# トルクOFF後、アドレス21へ32を書き、読戻し確認
sts-studio --port /dev/ttyUSB0 --baud 1000000 stop --ids 1
sts-studio --port /dev/ttyUSB0 --baud 1000000 write --id 1 --address 21 --value 32

# STSのBaudコード1（500000bps）に変更
sts-studio --port /dev/ttyUSB0 --baud 1000000 write --id 1 --address 6 --value 1
# 以後は新しい速度を指定
sts-studio --port /dev/ttyUSB0 --baud 500000 info --id 1
```

EEPROMはトルクOFFが必要です。`write` は保存値を検証し、IDやBaudを変更した場合は新しい接続先で確認して結果へ返します。次回コマンドの接続速度やIDを自動保存する機能はありません。`read --address` は定義されたレジスタの幅・符号形式で読みます。

## 動作と停止

```sh
sts-studio --port /dev/ttyUSB0 --baud 1000000 torque --ids 1,2 on
sts-studio --port /dev/ttyUSB0 --baud 1000000 move --ids 1,2 --position 2048 --speed 200 --acc 10 --method sync
sts-studio --port /dev/ttyUSB0 --baud 1000000 stop --ids 1,2
```

moveはトルクを自動ONにしません。位置・速度はraw値で、`--time-raw` と `--method write|sync|registered` を指定できます。送信結果は `sent: true, confirmed: false`。物理的な到達を確認したという意味ではありません。

`--method registered` は登録のみで、`action` がバス全体へ実行指令を送ります。別のCLIプロセスや別のツールで登録した指令も対象となります。stopは指定IDのトルクをOFFにして読み戻し、一部のIDが不在でも残りを試します。登録済み指令は消去しません。

CLIのstopはサーボのトルクOFFです。PWMアダプターの出力停止は `pwm enable 0` を使います。

## 保存・復元と補助コマンド

```sh
sts-studio --port /dev/ttyUSB0 --baud 1000000 backup --id 1 servo.xdat
sts-studio --port /dev/ttyUSB0 --baud 1000000 restore --id 1 servo.xdat
sts-studio --port /dev/ttyUSB0 --baud 1000000 restore --id 1 servo.xdat --apply
sts-studio inspect firmware.hex
sts-studio --port /dev/ttyUSB0 --baud 1000000 calibrate --id 1
sts-studio --port /dev/ttyUSB0 --baud 1000000 reset --id 1
sts-studio --port /dev/ttyUSB0 --baud 1000000 pwm mode 0
sts-studio --port /dev/ttyUSB0 --baud 1000000 pwm pulse 1500
sts-studio --port /dev/ttyUSB0 --baud 1000000 pwm enable 0
```

backupはSTSの設定領域40byteをxdatへ保存します。restoreは既定では差分表示のみで、`--apply` を付けると書き込みます。ID・Baudは既定で復元対象外、`--include-identity` で含めます。モデル・FWの一致、値の範囲、書込後の検証はGUIと共通です。部分失敗時は適用済みのアドレスをエラーに含めます。

calibrateはトルクOFFのSTS中点校正、resetはRecovery指令です。reset後のID・速度・完了状態は未確認のため再検索します。pwmはアダプターID253へ送信し、出力の実測確認はしません。inspectはファームウェアのファイル検査のみで、転送はしません。

デモ状態はコマンドごとに初期化されます。別プロセスで行った仮想サーボへの書込みは次のデモコマンドへ持ち越されません。CLIにはGUIのグラフやSweep/Stepの自動運転は含めていません。
