import unittest

from localmechai.detectors import detect_issues
from localmechai.models import DiskInfo, HealthSnapshot, ProcessInfo


def snapshot(*, cpu=20.0, memory=40.0, disk_percent=50.0, free_gb=100.0):
    return HealthSnapshot(
        timestamp="2026-08-14T00:00:00+00:00",
        platform="Windows",
        boot_time="2026-08-14T00:00:00+00:00",
        cpu_percent=cpu,
        cpu_count=8,
        memory_percent=memory,
        memory_used_gb=6.4,
        memory_total_gb=16.0,
        swap_percent=0.0,
        disks=[DiskInfo("C:\\", 500.0, 250.0, free_gb, disk_percent)],
        top_processes=[ProcessInfo(1, "example.exe", cpu, 100.0, "running")],
    )


class DetectorTests(unittest.TestCase):
    def test_healthy_snapshot(self):
        findings = detect_issues(snapshot())
        self.assertEqual(findings[0].code, "healthy")
        self.assertEqual(findings[0].severity, "info")

    def test_high_cpu_is_critical(self):
        findings = detect_issues(snapshot(cpu=95.0))
        high_cpu = next(item for item in findings if item.code == "high_cpu")
        self.assertEqual(high_cpu.severity, "critical")

    def test_memory_pressure_is_critical(self):
        findings = detect_issues(snapshot(memory=95.0))
        memory = next(item for item in findings if item.code == "memory_pressure")
        self.assertEqual(memory.severity, "critical")

    def test_low_disk_space_detected(self):
        findings = detect_issues(snapshot(disk_percent=96.0, free_gb=2.0))
        disk = next(item for item in findings if item.code == "low_disk_space")
        self.assertEqual(disk.severity, "critical")


if __name__ == "__main__":
    unittest.main()
