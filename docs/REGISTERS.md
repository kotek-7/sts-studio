# メモリ表・モデル識別仕様

機械可読定義は `spec/catalog.json`。`-1 / -1`は入力範囲未指定です。実効範囲は格納幅・符号bitによる範囲と明示範囲の共通部分です。

## SMXXBLHV / SMS

FW 2.40〜2.59、byte order: little。feedback 56..72、control 41、lock 55。

| Addr | Name | bytes | default | sign bit | area | access | min | max |
|---|---|---|---|---|---|---|---|---|
| 0 | Firmare Main Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 1 | Firmware Secondary Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 3 | Servo Main Version | 1 | None | -1 | EPROM | d | -1 | -1 |
| 4 | Servo Sub Version | 1 | None | -1 | EPROM | d | -1 | -1 |
| 5 | ID | 1 | 0 | -1 | EPROM | rw | 0 | 253 |
| 6 | Baud Rate | 1 | 4 | -1 | EPROM | rw | 0 | 11 |
| 7 | Return Delay Time | 1 | 250 | -1 | EPROM | rw | 0 | 254 |
| 8 | Status Return Level | 1 | 1 | -1 | EPROM | rw | 0 | 1 |
| 9 | Min Position Limit | 2 | 0 | 15 | EPROM | rw | -1 | -1 |
| 11 | Max Position Limit | 2 | 0 | 15 | EPROM | rw | -1 | -1 |
| 13 | Max Temperature limit | 1 | 80 | -1 | EPROM | rw | 0 | 100 |
| 14 | Max Input Voltage | 1 | 140 | -1 | EPROM | rw | 0 | 254 |
| 15 | Min Input Voltage | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 16 | Max Torque Limit | 2 | 1000 | -1 | EPROM | rw | 0 | 1000 |
| 18 | Setting Byte | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 19 | Protection Switch | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 20 | LED Alarm Condition | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 21 | Position P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 22 | Position D Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 23 | Position I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 24 | Punch | 2 | 0 | -1 | EPROM | rw | 0 | 1000 |
| 26 | CW Dead Band | 1 | 0 | -1 | EPROM | rw | 0 | 32 |
| 27 | CCW Dead Band | 1 | 0 | -1 | EPROM | rw | 0 | 32 |
| 28 | Overload Current | 2 | 0 | -1 | EPROM | rw | 0 | 511 |
| 30 | Angular Resolution | 1 | 1 | -1 | EPROM | rw | 1 | 100 |
| 31 | Position Offset Value | 2 | 0 | 15 | EPROM | rw | -2047 | 2047 |
| 33 | Work Mode | 1 | 0 | -1 | EPROM | rw | 0 | 2 |
| 34 | Protect Torque | 1 | 40 | -1 | EPROM | rw | 0 | 254 |
| 35 | Overload Protection Time | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 36 | Overload Torque | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 37 | Velocity P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 38 | Overcurrent Protection Time | 1 | 100 | -1 | EPROM | rw | 0 | 254 |
| 39 | Velocity I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 40 | Torque Enable | 1 | 0 | -1 | SRAM | rw | 0 | 254 |
| 41 | Goal  Acceleration | 1 | 0 | -1 | SRAM | rw | 0 | 254 |
| 42 | Goal Position | 2 | 0 | 15 | SRAM | rw | -32766 | 32766 |
| 44 | Running Time | 2 | 0 | 10 | SRAM | rw | -32766 | 32766 |
| 46 | Goal  Velocity | 2 | 0 | 15 | SRAM | rw | -32766 | 32766 |
| 48 | Torque Limit | 2 | 1000 | -1 | SRAM | rw | 0 | 1000 |
| 55 | Lock | 1 | 1 | -1 | SRAM | rw | 0 | 1 |
| 56 | Present Position | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 58 | Present Velocity | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 60 | Present PWM | 2 | 0 | 10 | SRAM | r | -1 | -1 |
| 62 | Present Input Voltage | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 63 | Present Temperature | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 64 | Sync Write Flag | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 65 | Hardware Error Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 66 | Moving Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 69 | Present Current | 2 | 0 | 15 | SRAM | r | -1 | -1 |

## SCSXX / SCS

FW 0.0〜0.19、byte order: big。feedback 56..72、control 41、lock 48。

| Addr | Name | bytes | default | sign bit | area | access | min | max |
|---|---|---|---|---|---|---|---|---|
| 0 | Firmare Main Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 1 | Firmware Secondary Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 3 | Servo Main Version | 1 | None | -1 | EPROM | r | -1 | -1 |
| 4 | Servo Sub Version | 1 | None | -1 | EPROM | d | -1 | -1 |
| 5 | ID | 1 | 0 | -1 | EPROM | rw | 0 | 253 |
| 6 | Baud Rate | 1 | 4 | -1 | EPROM | rw | 0 | 10 |
| 7 | Return Delay Time | 1 | 250 | -1 | EPROM | rw | 0 | 254 |
| 8 | Status Return Level | 1 | 1 | -1 | EPROM | rw | 0 | 1 |
| 9 | Min Position Limit | 2 | 0 | 15 | EPROM | rw | 0 | 1023 |
| 11 | Max Position Limit | 2 | 0 | 15 | EPROM | rw | 0 | 1023 |
| 13 | Max Temperature limit | 1 | 80 | -1 | EPROM | rw | 0 | 100 |
| 14 | Max Input Voltage | 1 | 140 | -1 | EPROM | rw | 0 | 254 |
| 15 | Min Input Voltage | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 16 | Max Torque Limit | 2 | 1000 | -1 | EPROM | rw | 0 | 1000 |
| 19 | Protection Switch | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 20 | LED Alarm Condition | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 21 | Position P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 22 | Position D Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 23 | Position I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 24 | Punch | 2 | 0 | -1 | EPROM | rw | 0 | 1000 |
| 26 | CW Dead Band | 1 | 2 | -1 | EPROM | rw | 0 | 32 |
| 27 | CCW Dead Band | 1 | 2 | -1 | EPROM | rw | 0 | 32 |
| 37 | Protect Torque | 1 | 40 | -1 | EPROM | rw | 0 | 254 |
| 38 | Overload Protection Time | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 39 | Overload Torque | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 40 | Torque Enable | 1 | 0 | -1 | SRAM | rw | 0 | 2 |
| 42 | Goal Position | 2 | 0 | -1 | SRAM | rw | 0 | 1023 |
| 44 | Running Time | 2 | 0 | 15 | SRAM | rw | -32766 | 32766 |
| 46 | Goal  Velocity | 2 | 0 | -1 | SRAM | rw | 0 | 32766 |
| 48 | Lock | 1 | 1 | -1 | SRAM | rw | 0 | 1 |
| 56 | Present Position | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 58 | Present Velocity | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 60 | Present PWM | 2 | 0 | 10 | SRAM | r | -1 | -1 |
| 62 | Present Input Voltage | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 63 | Present Temperature | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 64 | Sync Write Flag | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 65 | Hardware Error Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 66 | Moving Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |

## SMXX / SMS

FW 1.0〜1.19、byte order: little。feedback 56..72、control 41、lock 48。

| Addr | Name | bytes | default | sign bit | area | access | min | max |
|---|---|---|---|---|---|---|---|---|
| 0 | Firmare Main Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 1 | Firmware Secondary Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 3 | Servo Main Version | 1 | None | -1 | EPROM | r | -1 | -1 |
| 4 | Servo Sub Version | 1 | None | -1 | EPROM | d | -1 | -1 |
| 5 | ID | 1 | 0 | -1 | EPROM | rw | 0 | 253 |
| 6 | Baud Rate | 1 | 4 | -1 | EPROM | rw | 0 | 254 |
| 7 | Return Delay Time | 1 | 250 | -1 | EPROM | rw | 0 | 254 |
| 8 | Status Return Level | 1 | 1 | -1 | EPROM | rw | 0 | 1 |
| 9 | Min Position Limit | 2 | 0 | 15 | EPROM | rw | -1 | -1 |
| 11 | Max Position Limit | 2 | 0 | 15 | EPROM | rw | -1 | -1 |
| 13 | Max Temperature limit | 1 | 80 | -1 | EPROM | rw | 0 | 100 |
| 14 | Max Input Voltage | 1 | 140 | -1 | EPROM | rw | 0 | 254 |
| 15 | Min Input Voltage | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 16 | Max Torque Limit | 2 | 1000 | -1 | EPROM | rw | 0 | 1000 |
| 18 | Setting Byte | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 19 | Protection Switch | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 20 | LED Alarm Condition | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 21 | Position P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 22 | Position D Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 23 | Position I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 24 | Punch | 2 | 0 | -1 | EPROM | rw | 0 | 1000 |
| 26 | CW Dead Band | 1 | 0 | -1 | EPROM | rw | 0 | 32 |
| 27 | CCW Dead Band | 1 | 0 | -1 | EPROM | rw | 0 | 32 |
| 28 | Overload Current | 2 | 0 | -1 | EPROM | rw | 0 | 1023 |
| 33 | Position Offset Value | 2 | 0 | 15 | EPROM | rw | -2047 | 2047 |
| 35 | Work Mode | 1 | 0 | -1 | EPROM | rw | 0 | 2 |
| 36 | Overcurrent Protection Time | 1 | 100 | -1 | EPROM | rw | 0 | 254 |
| 37 | Protect Torque | 1 | 40 | -1 | EPROM | rw | 0 | 254 |
| 38 | Overload Protection Time | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 39 | Overload Torque | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 40 | Torque Enable | 1 | 0 | -1 | SRAM | rw | 0 | 254 |
| 41 | Goal  Acceleration | 1 | 0 | -1 | SRAM | rw | 0 | 254 |
| 42 | Goal Position | 2 | 0 | -1 | SRAM | rw | -32766 | 32766 |
| 44 | Running Time | 2 | 0 | 15 | SRAM | rw | -32766 | 32766 |
| 46 | Goal  Velocity | 2 | 0 | 15 | SRAM | rw | 0 | 32766 |
| 48 | Lock | 1 | 1 | -1 | SRAM | rw | 0 | 1 |
| 56 | Present Position | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 58 | Present Velocity | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 60 | Present PWM | 2 | 0 | 10 | SRAM | r | -1 | -1 |
| 62 | Present Input Voltage | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 63 | Present Temperature | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 64 | Sync Write Flag | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 65 | Hardware Error Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 66 | Moving Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 69 | Present Current | 2 | 0 | 15 | SRAM | r | -1 | -1 |

## SM12XX / SMS

FW 1.20〜1.39、byte order: little。feedback 56..72、control 41、lock 48。

| Addr | Name | bytes | default | sign bit | area | access | min | max |
|---|---|---|---|---|---|---|---|---|
| 0 | Firmare Main Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 1 | Firmware Secondary Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 3 | Servo Main Version | 1 | None | -1 | EPROM | r | -1 | -1 |
| 4 | Servo Sub Version | 1 | None | -1 | EPROM | d | -1 | -1 |
| 5 | ID | 1 | 0 | -1 | EPROM | rw | 0 | 253 |
| 6 | Baud Rate | 1 | 4 | -1 | EPROM | rw | 0 | 254 |
| 7 | Return Delay Time | 1 | 250 | -1 | EPROM | rw | 0 | 254 |
| 8 | Status Return Level | 1 | 1 | -1 | EPROM | rw | 0 | 1 |
| 9 | Min Position Limit | 2 | 0 | 15 | EPROM | rw | -1 | -1 |
| 11 | Max Position Limit | 2 | 0 | 15 | EPROM | rw | -1 | -1 |
| 13 | Max Temperature limit | 1 | 80 | -1 | EPROM | rw | 0 | 100 |
| 14 | Max Input Voltage | 1 | 140 | -1 | EPROM | rw | 0 | 254 |
| 15 | Min Input Voltage | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 16 | Max Torque Limit | 2 | 1000 | -1 | EPROM | rw | 0 | 1000 |
| 18 | Setting Byte | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 19 | Protection Switch | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 20 | LED Alarm Condition | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 21 | Position P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 22 | Position D Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 23 | Position I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 24 | Punch | 2 | 0 | -1 | EPROM | rw | 0 | 1000 |
| 26 | CW Dead Band | 1 | 0 | -1 | EPROM | rw | 0 | 32 |
| 27 | CCW Dead Band | 1 | 0 | -1 | EPROM | rw | 0 | 32 |
| 28 | Overload Current | 2 | 0 | -1 | EPROM | rw | 0 | 1023 |
| 30 | Velocity P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 31 | Velocity I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 33 | Position Offset Value | 2 | 0 | 15 | EPROM | rw | -2047 | 2047 |
| 35 | Work Mode | 1 | 0 | -1 | EPROM | rw | 0 | 2 |
| 36 | Overcurrent Protection Time | 1 | 100 | -1 | EPROM | rw | 0 | 254 |
| 37 | Protect Torque | 1 | 40 | -1 | EPROM | rw | 0 | 254 |
| 38 | Overload Protection Time | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 39 | Overload Torque | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 40 | Torque Enable | 1 | 0 | -1 | SRAM | rw | 0 | 254 |
| 41 | Goal  Acceleration | 1 | 0 | -1 | SRAM | rw | 0 | 254 |
| 42 | Goal Position | 2 | 0 | -1 | SRAM | rw | -32766 | 32766 |
| 44 | Running Time | 2 | 0 | 15 | SRAM | rw | -32766 | 32766 |
| 46 | Goal  Velocity | 2 | 0 | 15 | SRAM | rw | 0 | 32766 |
| 48 | Lock | 1 | 1 | -1 | SRAM | rw | 0 | 1 |
| 56 | Present Position | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 58 | Present Velocity | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 60 | Present PWM | 2 | 0 | 10 | SRAM | r | -1 | -1 |
| 62 | Present Input Voltage | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 63 | Present Temperature | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 64 | Sync Write Flag | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 65 | Hardware Error Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 66 | Moving Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 69 | Present Current | 2 | 0 | 15 | SRAM | r | -1 | -1 |

## STSXX / STS

FW 3.0〜3.19、byte order: little。feedback 56..72、control 41、lock 55。

位置オフセットaddress31は符号bit11を使用します。

目標速度レジスタの範囲は±1000です。動作指令の16bit速度フィールドとは異なります。

| Addr | Name | bytes | default | sign bit | area | access | min | max |
|---|---|---|---|---|---|---|---|---|
| 0 | Firmare Main Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 1 | Firmware Secondary Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 3 | Servo Main Version | 1 | None | -1 | EPROM | r | -1 | -1 |
| 4 | Servo Sub Version | 1 | None | -1 | EPROM | d | -1 | -1 |
| 5 | ID | 1 | 0 | -1 | EPROM | rw | 0 | 253 |
| 6 | Baud Rate | 1 | 4 | -1 | EPROM | rw | 0 | 7 |
| 7 | Return Delay Time | 1 | 250 | -1 | EPROM | rw | 0 | 254 |
| 8 | Status Return Level | 1 | 1 | -1 | EPROM | rw | 0 | 1 |
| 9 | Min Position Limit | 2 | 0 | 15 | EPROM | rw | -1 | -1 |
| 11 | Max Position Limit | 2 | 0 | 15 | EPROM | rw | -1 | -1 |
| 13 | Max Temperature limit | 1 | 80 | -1 | EPROM | rw | 0 | 100 |
| 14 | Max Input Voltage | 1 | 140 | -1 | EPROM | rw | 0 | 254 |
| 15 | Min Input Voltage | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 16 | Max Torque Limit | 2 | 1000 | -1 | EPROM | rw | 0 | 1000 |
| 18 | Setting Byte | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 19 | Protection Switch | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 20 | LED Alarm Condition | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 21 | Position P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 22 | Position D Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 23 | Position I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 24 | Punch | 2 | 0 | -1 | EPROM | rw | 0 | 1000 |
| 26 | CW Dead Band | 1 | 0 | -1 | EPROM | rw | 0 | 32 |
| 27 | CCW Dead Band | 1 | 0 | -1 | EPROM | rw | 0 | 32 |
| 28 | Overload Current | 2 | 0 | -1 | EPROM | rw | 0 | 511 |
| 30 | Angular Resolution | 1 | 1 | -1 | EPROM | rw | 1 | 100 |
| 31 | Position Offset Value | 2 | 0 | 11 | EPROM | rw | -2047 | 2047 |
| 33 | Work Mode | 1 | 0 | -1 | EPROM | rw | 0 | 3 |
| 34 | Protect Torque | 1 | 40 | -1 | EPROM | rw | 0 | 254 |
| 35 | Overload Protection Time | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 36 | Overload Torque | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 37 | Velocity P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 38 | Overcurrent Protection Time | 1 | 100 | -1 | EPROM | rw | 0 | 254 |
| 39 | Velocity I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 40 | Torque Enable | 1 | 0 | -1 | SRAM | rw | 0 | 254 |
| 41 | Goal  Acceleration | 1 | 0 | -1 | SRAM | rw | 0 | 254 |
| 42 | Goal Position | 2 | 0 | 15 | SRAM | rw | -32766 | 32766 |
| 46 | Goal  Velocity | 2 | 0 | 15 | SRAM | rw | -1000 | 1000 |
| 48 | Torque Limit | 2 | 1000 | -1 | SRAM | rw | 0 | 1000 |
| 55 | Lock | 1 | 1 | -1 | SRAM | rw | 0 | 1 |
| 56 | Present Position | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 58 | Present Velocity | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 60 | Present PWM | 2 | 0 | 10 | SRAM | r | -1 | -1 |
| 62 | Present Input Voltage | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 63 | Present Temperature | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 64 | Sync Write Flag | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 65 | Hardware Error Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 66 | Moving Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 69 | Present Current | 2 | 0 | 15 | SRAM | r | -1 | -1 |

## SC20XX / SCS

FW 3.20〜3.39、byte order: big。feedback 56..72、control 41、lock 48。

| Addr | Name | bytes | default | sign bit | area | access | min | max |
|---|---|---|---|---|---|---|---|---|
| 0 | Firmare Main Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 1 | Firmware Secondary Version NO. | 1 | None | -1 | EPROM | r | -1 | -1 |
| 3 | Servo Main Version | 1 | None | -1 | EPROM | r | -1 | -1 |
| 4 | Servo Sub Version | 1 | None | -1 | EPROM | d | -1 | -1 |
| 5 | ID | 1 | 0 | -1 | EPROM | rw | 0 | 253 |
| 6 | Baud Rate | 1 | 4 | -1 | EPROM | rw | 0 | 7 |
| 7 | Return Delay Time | 1 | 250 | -1 | EPROM | rw | 0 | 254 |
| 8 | Status Return Level | 1 | 1 | -1 | EPROM | rw | 0 | 1 |
| 9 | Min Position Limit | 2 | 0 | 15 | EPROM | rw | 0 | 1023 |
| 11 | Max Position Limit | 2 | 0 | 15 | EPROM | rw | 0 | 1023 |
| 13 | Max Temperature limit | 1 | 80 | -1 | EPROM | rw | 0 | 100 |
| 14 | Max Input Voltage | 1 | 140 | -1 | EPROM | rw | 0 | 254 |
| 15 | Min Input Voltage | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 16 | Max Torque Limit | 2 | 1000 | -1 | EPROM | rw | 0 | 1000 |
| 18 | Setting Byte | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 19 | Protection Switch | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 20 | LED Alarm Condition | 1 | 37 | -1 | EPROM | rw | 0 | 254 |
| 21 | Position P Gain | 1 | 32 | -1 | EPROM | rw | 0 | 254 |
| 22 | Position D Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 23 | Position I Gain | 1 | 0 | -1 | EPROM | rw | 0 | 254 |
| 24 | Punch | 2 | 0 | -1 | EPROM | rw | 0 | 1000 |
| 26 | CW Dead Band | 1 | 2 | -1 | EPROM | rw | 0 | 32 |
| 27 | CCW Dead Band | 1 | 2 | -1 | EPROM | rw | 0 | 32 |
| 31 | Overcurrent Protection Time | 1 | 100 | -1 | EPROM | rw | 0 | 254 |
| 32 | Overload Current | 2 | 0 | -1 | EPROM | rw | 0 | 1023 |
| 37 | Protect Torque | 1 | 40 | -1 | EPROM | rw | 0 | 254 |
| 38 | Overload Protection Time | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 39 | Overload Torque | 1 | 80 | -1 | EPROM | rw | 0 | 254 |
| 40 | Torque Enable | 1 | 0 | -1 | SRAM | rw | 0 | 2 |
| 42 | Goal Position | 2 | 0 | -1 | SRAM | rw | 0 | 1023 |
| 44 | Running Time | 2 | 0 | 15 | SRAM | rw | -32766 | 32766 |
| 46 | Goal  Velocity | 2 | 0 | -1 | SRAM | rw | 0 | 32766 |
| 48 | Lock | 1 | 1 | -1 | SRAM | rw | 0 | 1 |
| 56 | Present Position | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 58 | Present Velocity | 2 | 0 | 15 | SRAM | r | -1 | -1 |
| 60 | Present PWM | 2 | 0 | 10 | SRAM | r | -1 | -1 |
| 62 | Present Input Voltage | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 63 | Present Temperature | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 64 | Sync Write Flag | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 65 | Hardware Error Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 66 | Moving Status | 1 | 0 | -1 | SRAM | r | -1 | -1 |
| 69 | Present Current | 2 | 0 | 15 | SRAM | r | -1 | -1 |

## 操作・監視プロファイル

設定メモリ表とは独立した定義です。メモリ表がなくても対応する操作・監視を使用できます。torque=0の定義は監視のみです。

| FW | endian | feedback | control | torque | position divisor | speed multiplier |
|---|---|---|---|---|---|---|
| 0.0..39 | 1 | 56..72 | 41 | 40 | 4 | 0.2 |
| 0.240..244 | 1 | 86..102 | 71 | 70 | 4 | 0.2 |
| 1.0..19 | 0 | 56..72 | 41 | 40 | 1 | 0.2 |
| 1.20..39 | 0 | 56..72 | 41 | 40 | 1 | 0.2 |
| 3.0..19 | 0 | 56..72 | 41 | 40 | 1 | 0.2 |
| 3.20..39 | 1 | 56..72 | 41 | 40 | 4 | 0.2 |
| 2.0..19 | 0 | 56..72 | 41 | 40 | 1 | 10.0 |
| 2.20..39 | 0 | 56..72 | 41 | 40 | 1 | 5.0 |
| 2.40..59 | 0 | 56..72 | 41 | 40 | 1 | 10.0 |
| 20.0..19 | 0 | 64..80 | 36 | 0 | 1 | 0.0 |

## モデル名識別

| major | minor range | endian | name |
|---|---|---|---|
| 5 | 0..0 | 1 | SCSXX |
| 5 | 4..4 | 1 | SCS009 |
| 5 | 8..8 | 1 | SCS2332 |
| 5 | 12..12 | 1 | SCS45 |
| 5 | 15..15 | 1 | SCS15 |
| 5 | 16..16 | 1 | SCS315 |
| 5 | 25..25 | 1 | SCS115 |
| 5 | 35..35 | 1 | SCS215 |
| 5 | 40..40 | 1 | SCS40 |
| 5 | 60..60 | 1 | SCS6560 |
| 5 | 240..244 | 1 | SCDZZ |
| 6 | 0..0 | 0 | SMXX-360M |
| 6 | 3..3 | 0 | SM30-360M |
| 6 | 8..8 | 0 | SM60-360M |
| 6 | 12..12 | 0 | SM80-360M |
| 6 | 16..16 | 0 | SM100-360M |
| 6 | 20..20 | 0 | SM150-360M |
| 6 | 24..24 | 0 | SM85-360M |
| 6 | 26..26 | 0 | SM60-360M |
| 8 | 0..19 | 0 | SM30BL |
| 8 | 25..25 | 0 | SM29BL(LJ) |
| 8 | 29..29 | 0 | SM29BL(FT) |
| 8 | 30..30 | 0 | SM30BL(FT) |
| 8 | 20..24 | 0 | SM30BL(LJ) |
| 8 | 40..40 | 0 | SM40BLHV |
| 8 | 42..42 | 0 | SM45BLHV |
| 8 | 44..44 | 0 | SM85BLHV |
| 8 | 120..120 | 0 | SM120BLHV |
| 8 | 220..220 | 0 | SM200BLHV |
| 9 | 0..0 | 0 | STSXX |
| 9 | 2..2 | 0 | STS3032 |
| 9 | 3..3 | 0 | STS3215 |
| 9 | 4..4 | 0 | STS3040 |
| 9 | 5..5 | 0 | STS20 |
| 9 | 6..6 | 0 | STS3046 |
| 9 | 20..20 | 1 | SCSXX-2 |
| 9 | 15..15 | 1 | SCS15-2 |
| 9 | 35..35 | 1 | SCS225 |
| 9 | 40..40 | 1 | SCS40-2 |
| 1 | 0..19 | 0 | 1.0(HUB) |
