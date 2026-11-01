# CLI

The installed `sts-studio` command is the CLI. Extracted packages include it in `cli/`. From source, replace `sts-studio` with `uv run --locked python -m sts_studio cli`.

Close the GUI connection before opening the same port. Common options go before the subcommand. Use `COM3` on Windows or the appropriate `/dev/cu.*` device on macOS in place of the Linux port below.

```sh
sts-studio --help
sts-studio ports
sts-studio --demo scan
sts-studio --port /dev/ttyUSB0 --baud 1000000 info --id 1
sts-studio --port /dev/ttyUSB0 --baud 1000000 feedback --id 1
sts-studio --port /dev/ttyUSB0 --baud 1000000 watch --id 1 --interval-ms 100 --count 50
sts-studio --port /dev/ttyUSB0 --baud 1000000 backup --id 1 servo.xdat
sts-studio --port /dev/ttyUSB0 --baud 1000000 restore --id 1 servo.xdat
```

`restore` shows differences by default. Add `--apply` to write them. ID and baud are excluded unless `--include-identity` is given. Model and firmware must match. EEPROM writes require torque OFF and are read back.

```sh
sts-studio --port /dev/ttyUSB0 --baud 1000000 torque --ids 1,2 on
sts-studio --port /dev/ttyUSB0 --baud 1000000 move --ids 1,2 --position 2048 --speed 200 --acc 10 --method sync
sts-studio --port /dev/ttyUSB0 --baud 1000000 stop --ids 1,2
```

`move` does not enable torque. `--method registered` queues commands for `action`, which broadcasts to the bus. `stop` requests and reads back torque OFF; it does not clear registered commands. Closing the CLI or pressing Ctrl+C does not automatically disable torque or undo settings.

Output is JSON; `watch` emits JSON Lines. `--trace` writes packets to stderr. Exit codes: 0 success, 1 operation failure, 2 invalid arguments, 130 interruption. `stop` reports each ID and returns 1 on partial failure. Motion output confirms transmission, not physical arrival.

Each demo invocation starts with fresh virtual IDs 1 and 2. Changes do not persist to another process. The CLI does not include the desktop's plots or automatic Sweep/Step. See the [Japanese command reference](CLI.md) for register editing, calibration, Recovery, and PWM examples.
