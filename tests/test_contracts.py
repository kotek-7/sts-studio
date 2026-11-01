import csv
import os
import sys

if sys.platform == "linux":
    import pty
import select
import tempfile
import threading
import unittest
from pathlib import Path

from sts_studio.automation import CommunicationStats, Pattern
from sts_studio.catalog import CATALOG, PROTOCOL, ROOT, Profile, identify
from sts_studio.files import ParameterImage, inspect_firmware, write_csv
from sts_studio.service import Service
from sts_studio.simulator import VirtualLink
from sts_studio.wire import LinkError, Parser, SerialLink

VECTORS = {x["id"]: bytes.fromhex(x["frame"]) for x in PROTOCOL["test_vectors"]}


class Contracts(unittest.TestCase):
    def setUp(self):
        self.link = VirtualLink()
        self.service = Service(self.link)
        self.service.discover(1)
        self.service.discover(2)
        self.link.history.clear()

    def writes(self):
        return [p for p in self.link.history if p[4] in (3, 4, 5, 6, 131)]

    @unittest.skipUnless(sys.platform == "linux", "Linux PTY integration")
    def test_connect_has_no_writes(self):
        master, slave = pty.openpty()
        link = SerialLink(os.ttyname(slave))
        try:
            self.assertFalse(select.select([master], [], [], 0.02)[0])
        finally:
            link.close()
            os.close(master)
            os.close(slave)

    def test_scan_read_not_ping(self):
        found = self.service.scan(0, 3, threading.Event(), lambda *x: None)
        self.assertEqual([s.sid for s in found], [1, 2])
        self.assertIn(VECTORS["search"], self.link.history)
        self.assertFalse(self.writes())

    def test_catalog_selection(self):
        servo = self.service.get(1)
        self.assertEqual(servo.model, "STS3215")
        self.assertEqual(servo.profile.name, "STSXX")
        self.assertEqual(servo.profile.field(31).sign_bit, 11)
        unknown = identify(bytes([99, 0, 0, 9, 3, 1, 0, 0, 1]))
        self.assertIsNone(unknown[1])
        self.assertEqual(unknown[0], "STS3215")

    def test_all_catalog_profiles(self):
        self.assertEqual(len(CATALOG["profiles"]), 6)
        self.assertEqual(sum(len(p["registers"]) for p in CATALOG["profiles"]), 269)
        self.assertEqual(len(CATALOG["models"]), 40)
        for raw in CATALOG["profiles"]:
            p = Profile(raw)
            header = bytes([raw["firmware_major"], raw["firmware_minor_min"], 0, 9, 3, 1, 0, 0, 1])
            self.assertEqual(identify(header)[1].name, p.name)
            for r in p.registers:
                lo, hi = r.limits
                for v in (lo, hi):
                    self.assertEqual(r.unpack(r.pack(v, p.order), p.order), v)

    def test_feedback_exact_vector(self):
        result = self.service.feedback(1)
        self.assertEqual(self.link.history[-1], VECTORS["feedback"])
        self.assertEqual(result["values"][56], 2048)

    def test_write_vector(self):
        self.service.control([1], 1234, 321, 17, 456)
        self.assertEqual(self.writes(), [VECTORS["write"]])

    def test_sync_vector(self):
        self.service.control([1], 1234, 321, 17, 456, "sync")
        self.assertEqual(self.writes(), [VECTORS["sync"]])

    def test_sync_multiple_and_prevalidation(self):
        self.service.control([1, 2], 1234, 321, 17, 456, "sync")
        self.assertEqual(len(self.writes()), 1)
        self.assertEqual(self.link.mem[1][41:48], self.link.mem[2][41:48])
        self.link.history.clear()
        with self.assertRaises(ValueError):
            self.service.control([1], 50000, 321, 17, 456)
        self.assertEqual(self.writes(), [])
        with self.assertRaises(ValueError):
            self.service.bus.sync(41, [(1, b"123"), (1, b"456")])

    def test_registered_not_executed(self):
        previous = bytes(self.link.mem[1][41:48])
        self.service.control([1], 1234, 321, 17, 456, "registered")
        self.assertEqual(self.writes(), [VECTORS["registered"]])
        self.assertEqual(bytes(self.link.mem[1][41:48]), previous)
        self.assertEqual(self.link.mem[1][64], 1)

    def test_action_broadcast(self):
        self.service.control([1, 2], 1234, 321, 17, 456, "registered")
        self.link.history.clear()
        self.service.action()
        self.assertEqual(self.writes(), [VECTORS["action"]])
        self.assertFalse(self.service.pending)
        self.assertEqual(self.link.mem[2][42:44], b"\xd2\x04")

    def test_torque_failure_explicit(self):
        self.link.mem.pop(1)
        with self.assertRaisesRegex(LinkError, "未確認"):
            self.service.set_torque([1, 2], False)
        self.assertTrue(
            any(p[2] == 2 and p[4] == 3 and p[5:7] == b"\x28\0" for p in self.link.history)
        )

    def test_sweep_sequence(self):
        p = Pattern(100, 200)
        self.assertEqual([p.next() for _ in range(5)], [100, 200, 100, 200, 100])

    def test_step_no_overshoot(self):
        p = Pattern(1000, 1100, 30)
        self.assertEqual(
            [p.next() for _ in range(9)], [1000, 1030, 1060, 1090, 1100, 1070, 1040, 1010, 1000]
        )
        p = Pattern(30, 0, 20)
        self.assertEqual([p.next() for _ in range(5)], [30, 10, 0, 20, 30])
        with self.assertRaises(ValueError):
            Pattern(0, 1, 0)

    def test_csv_columns(self):
        with tempfile.TemporaryDirectory() as d:
            row = {
                56: 1234,
                60: -100,
                58: -20,
                69: 10,
                63: 25,
                62: 74,
                "id": 1,
                "timestamp": 100,
                "goal": 2000,
                "error": 0,
            }
            path = Path(d) / "out.csv"
            write_csv(path, [row])
            lines = list(csv.reader(path.read_text().splitlines()))
            self.assertEqual(lines[1][8], "7.4")
            self.assertEqual(lines[1][2], "1234")
            write_csv(path, [row], True)
            lines = list(csv.reader(path.read_text().splitlines()))
            self.assertEqual(lines[1][-1], "END")
            self.assertEqual(len(lines[1]), 9)

    def test_parameter_lock_finally(self):
        self.service.write_register(1, 21, 55)
        self.assertEqual(self.writes(), [VECTORS["unlock"], VECTORS["parameter"], VECTORS["lock"]])
        original = self.service.bus.send

        def fail(sid, address, data, registered=False):
            if address == 21:
                raise LinkError("injected write failure")
            return original(sid, address, data, registered)

        self.service.bus.send = fail
        with self.assertRaisesRegex(LinkError, "injected"):
            self.service.write_register(1, 21, 42)
        self.assertEqual(self.link.mem[1][55], 1)

    def test_eeprom_rejects_torque_on(self):
        self.link.mem[1][40] = 1
        with self.assertRaisesRegex(LinkError, "OFF"):
            self.service.write_register(1, 21, 55)
        self.assertEqual(self.writes(), [])

    def test_id_baud_tracking(self):
        self.assertEqual(self.service.write_register(1, 5, 7), 7)
        self.assertIn(7, self.service.servos)
        self.assertEqual(self.link.mem[7][55], 1)
        self.service.write_register(7, 6, 4)
        self.assertEqual(self.link.baud, 115200)
        self.assertEqual(self.link.mem[7][55], 1)
        with self.assertRaisesRegex(LinkError, "使用中"):
            self.service.write_register(7, 5, 2)

    def test_xdat_roundtrip(self):
        path = ROOT / "tests/fixtures/sts3215.xdat"
        image = ParameterImage.load(path)
        self.assertEqual(image.start, 0)
        self.assertEqual(len(image.data), 40)
        self.assertEqual(image.data[:5], b"\x03\x06\0\x09\x03")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.xdat"
            image.save(out)
            self.assertEqual(out.read_bytes(), path.read_bytes())
            out.write_bytes(b"\x00\x28bad")
            with self.assertRaises(ValueError):
                ParameterImage.load(out)

    def test_restore_partial_failure(self):
        with self.assertRaisesRegex(LinkError, r"適用済みアドレス \[21\]"):
            self.service.restore(1, [(21, 55), (22, 300)], threading.Event())
        self.assertEqual(self.link.mem[1][21], 55)
        self.assertEqual(self.link.mem[1][22], 32)

    def test_recovery_wire_only(self):
        text = self.service.reset(1)
        self.assertEqual(self.writes(), [VECTORS["reset"]])
        self.assertIn("未確認", text)
        self.assertNotIn(1, self.service.servos)

    def test_calibration_verification(self):
        self.assertEqual(self.service.calibration(1), 2048)
        self.link.mem[1][40] = 1
        with self.assertRaises(LinkError):
            self.service.calibration(1)

    def test_comm_stats(self):
        s = CommunicationStats()
        s.add(0.001, 31)
        s.add(0.003, 31)
        s.add(0.05, 8, "timeout")
        r = s.report()
        self.assertEqual(r["success"], 2)
        self.assertEqual(r["timeouts"], 1)
        self.assertEqual(r["mean_us"], 2000)

    def test_pwm_test_vectors(self):
        for kind, value, key in [
            ("mode", 0, "pwm_mode"),
            ("pulse", 1500, "pwm_pulse"),
            ("enable", 1, "pwm_on"),
            ("enable", 0, "pwm_off"),
            ("mode", 1, "bus_mode"),
        ]:
            self.service.pwm(kind, value)
            self.assertEqual(self.link.history[-1], VECTORS[key])

    def test_pwm_pattern_bounds(self):
        p = Pattern(500, 2500, 333)
        self.assertTrue(all(500 <= p.next() <= 2500 for _ in range(100)))
        with self.assertRaises(ValueError):
            self.service.pwm("pulse", 3000)

    def test_hex_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fw.hex"
            p.write_text(":0400000001020304F2\n:00000001FF\n")
            r = inspect_firmware(p)
            self.assertEqual(r["data_bytes"], 4)
            self.assertFalse(r["flash_supported"])
            p.write_text(":0400000001020304F3\n:00000001FF\n")
            with self.assertRaises(ValueError):
                inspect_firmware(p)
            p.write_text(":0400000001020304F2\n")
            with self.assertRaises(ValueError):
                inspect_firmware(p)

    def test_cancellation_before_motion(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(LinkError):
            self.service.control([1, 2], 100, 200, 10, 0, cancel=cancel)
        self.assertFalse(self.writes())

    def test_parser_fragmented_noise_checksum(self):
        p = Parser()
        good = bytes.fromhex("ff ff 01 04 00 00 08 f2")
        self.assertEqual(p.feed(b"\x12\xff\xff\xff\x00" + good[:4]), [])
        self.assertEqual(p.feed(good[4:]), [good])
        bad = good[:-1] + b"\0"
        self.assertEqual(p.feed(bad + good), [good])

    def test_packet_checksums(self):
        for key, p in VECTORS.items():
            self.assertEqual(sum(p[2:]) & 255, 255, key)
            self.assertEqual(p[3] + 4, len(p), key)


if __name__ == "__main__":
    unittest.main()
