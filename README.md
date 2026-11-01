# STS Studio

Ubuntu向けのFEETECHサーボ設定・監視アプリです。サーボの検索、パラメータ編集、複数台への動作指令、状態のグラフ表示、測定データの保存を行えます。

## 起動

必要なUbuntuパッケージは `python3-pyqt5` と `python3-serial` です。

```sh
cd ~/dev/sts-studio
./run.sh
```

デモモードでは実機を接続せず、仮想サーボID1/2を操作できます。

```sh
./run.sh --demo
```

## 接続と操作

1. USBシリアルを接続し、Portを更新します。`/dev/ttyUSB0`、`/dev/ttyACM0` などを選択します。
2. サーボの通信速度に合わせてBaudを設定し、Openで接続します。初期値は115,200です。
3. SearchでID範囲を検索するか、IDを指定して読み取ります。
4. サーボを選択し、設定・監視・動作指令を行います。Ctrl / Shiftで複数台を選択できます。

接続しただけでは動作指令を送信しません。アクセス拒否の場合は `ls -l /dev/ttyUSB0` と `id` でポートの権限を確認してください。

STOPでトルクをOFFにしても、モニターがONならFBと記録は継続します。Liveは初期ONで、スライダーを動かすと位置指令を送信します。Step動作は端点を跨いで折り返すため、設定範囲を超える1回の指令を含みます。

## 機能

| 画面 | 内容 |
|---|---|
| 操作 | 位置・速度・加速度の指定、Write / Sync Write / Reg Write / Action、トルクON/OFF、往復・ステップ動作 |
| 設定 | レジスタの読取・編集、ID・通信速度変更、xdat保存・差分復元、中点校正、Recovery |
| モニター | 位置・目標位置・速度・負荷・電流・温度・電圧、グラフ範囲設定、CSV / TXT記録 |
| 診断・ファイル検査 | 通信時間・成功率の集計、ファームウェアのサイズ・SHA256・Intel HEX検査 |
| PWM | 対応アダプターのパルス幅・出力切替、往復・ステップ動作 |
| 通信ログ | 操作結果とHEXパケットの表示、仕様書・機能一覧へのリンク |

EEPROMはトルクOFFで編集します。書き込み後は値を読み戻して確認します。STOPは対象へのトルクOFFを試み、確認できなかったIDを表示します。Reg Writeの登録指令はSTOPでは消去されず、後のActionで実行される可能性があります。

## 仕様と開発

- [機能一覧](docs/FEATURE_MATRIX.md)
- [詳細機能仕様](docs/SPECIFICATION.md): 入力範囲、前提、通信、成功条件、エラー処理、実装とテスト。
- [設計仕様](docs/DESIGN.md): 状態遷移、スレッド、データ構造、ファイル形式。
- [レジスタ・モデル表](docs/REGISTERS.md): 10個の操作・監視プロファイル、6個の設定メモリ表、269レジスタ、40モデル。
- [API索引](docs/API_INDEX.md)
- [検証範囲](docs/VALIDATION.md)

`spec/` に機械可読定義、`src/sts_studio/` に実装、`tests/` にテストがあります。

```sh
python3 tools/render_spec.py
PYTHONPATH=src QT_QPA_PLATFORM=offscreen /usr/bin/python3 -m unittest discover -s tests -v
python3 tools/package.py
```

## 対応範囲

STSを中心に機能を提供します。SCS/SMSのメモリ定義も含みますが、各機種の実機動作は未検証です。xdat設定ファイルはSTSの40byte設定領域に対応し、モデルとファームウェアの一致を確認してから復元します。他ソフトウェアとの往復読込は未検証です。

ファームウェアはファイル検査のみ対応し、書き込みには対応していません。Modbusと、PWMアダプターへのMin/Max永続設定も未対応です。実機での動作・校正・Recovery・PWM波形、および電源断後のEEPROM保持は未検証です。
