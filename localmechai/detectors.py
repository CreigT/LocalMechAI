from __future__ import annotations

from collections import Counter

from .models import Finding, HealthReport, HealthSnapshot


def detect_issues(snapshot: HealthSnapshot, history: list[HealthReport] | None = None) -> list[Finding]:
    history = history or []
    findings: list[Finding] = []

    if snapshot.cpu_percent >= 90:
        top = snapshot.top_processes[:3]
        findings.append(
            Finding(
                code="high_cpu",
                title="CPU usage is very high",
                severity="critical",
                evidence=[
                    f"CPU is at {snapshot.cpu_percent}%.",
                    "Top processes: " + ", ".join(f"{p.name} ({p.cpu_percent}%)" for p in top),
                ],
                likely_cause="One or more active processes are saturating the processor.",
                remediation=[
                    "Save open work before closing anything.",
                    "Open Task Manager and sort by CPU.",
                    "If the top process is an app you recognize, close or restart it.",
                    "If the process is unfamiliar, do not delete files; inspect its publisher and scan with Windows Security.",
                ],
            )
        )
    elif snapshot.cpu_percent >= 75:
        findings.append(
            Finding(
                code="elevated_cpu",
                title="CPU usage is elevated",
                severity="warning",
                evidence=[f"CPU is at {snapshot.cpu_percent}%."],
                likely_cause="Background tasks, browser tabs, updates, or an app workload may be slowing the PC.",
                remediation=[
                    "Wait a few minutes if Windows Update or indexing is active.",
                    "Close unused browser tabs and heavy applications.",
                    "Run another scan to see whether the pressure persists.",
                ],
            )
        )

    if snapshot.memory_percent >= 90:
        findings.append(
            Finding(
                code="memory_pressure",
                title="Memory pressure is critical",
                severity="critical",
                evidence=[
                    f"RAM usage is {snapshot.memory_percent}%.",
                    f"{snapshot.memory_used_gb} GB of {snapshot.memory_total_gb} GB is in use.",
                ],
                likely_cause="Too many applications are open, or one process is consuming unusual memory.",
                remediation=[
                    "Save work in open apps.",
                    "Sort Task Manager by Memory and close nonessential apps.",
                    "Restart the heaviest app if memory does not drop after closing documents or tabs.",
                    "Consider disabling unnecessary startup apps if this repeats after boot.",
                ],
            )
        )
    elif snapshot.memory_percent >= 80:
        findings.append(
            Finding(
                code="elevated_memory",
                title="Memory usage is elevated",
                severity="warning",
                evidence=[f"RAM usage is {snapshot.memory_percent}%."],
                likely_cause="The PC may begin paging to disk if workload grows.",
                remediation=[
                    "Close unused apps before starting heavier work.",
                    "Check browser tab count and background launchers.",
                    "Track whether the same process grows over repeated scans.",
                ],
            )
        )

    for disk in snapshot.disks:
        if disk.percent >= 92 or disk.free_gb < 5:
            findings.append(
                Finding(
                    code="low_disk_space",
                    title=f"Disk space is low on {disk.mountpoint}",
                    severity="critical" if disk.free_gb < 3 else "warning",
                    evidence=[f"{disk.mountpoint} is {disk.percent}% full with {disk.free_gb} GB free."],
                    likely_cause="Temporary files, downloads, app caches, or large media may be consuming space.",
                    remediation=[
                        "Empty Recycle Bin after checking its contents.",
                        "Run Windows Storage Sense or Disk Cleanup.",
                        "Move large personal files to another drive or backup location.",
                        "Avoid deleting files from Windows or Program Files manually.",
                    ],
                )
            )

    explorer_hits = [p for p in snapshot.top_processes if p.name.lower() == "explorer.exe"]
    if explorer_hits and explorer_hits[0].cpu_percent >= 30:
        findings.append(
            Finding(
                code="explorer_pressure",
                title="Windows Explorer is using unusual resources",
                severity="warning",
                evidence=[f"explorer.exe is using {explorer_hits[0].cpu_percent}% CPU."],
                likely_cause="A shell extension, stuck file operation, thumbnail generation, or Explorer loop may be active.",
                remediation=[
                    "Wait for file copy, indexing, or thumbnail generation to finish.",
                    "Restart Windows Explorer from Task Manager if the desktop or taskbar is frozen.",
                    "If it repeats after opening a folder, check that folder for huge archives or broken shortcuts.",
                ],
            )
        )

    service_lookup = {service.name.lower(): service.status.lower() for service in snapshot.services}
    if service_lookup.get("eventlog") not in (None, "running"):
        findings.append(
            Finding(
                code="event_log_service",
                title="Windows Event Log service is not running",
                severity="critical",
                evidence=[f"EventLog status is {service_lookup.get('eventlog')}."],
                likely_cause="Windows diagnostics and log collection may be impaired.",
                remediation=[
                    "Open Services as administrator.",
                    "Find Windows Event Log and start the service.",
                    "If it fails to start, run System File Checker with: sfc /scannow.",
                ],
            )
        )

    event_findings = _detect_event_log_issues(snapshot)
    findings.extend(event_findings)

    recurring = _detect_recurring(history)
    findings.extend(recurring)

    if not findings:
        findings.append(
            Finding(
                code="healthy",
                title="No urgent issues detected",
                severity="info",
                evidence=[
                    f"CPU {snapshot.cpu_percent}%, RAM {snapshot.memory_percent}%, "
                    f"{len(snapshot.disks)} disk volume(s) checked."
                ],
                likely_cause="Current system metrics are within normal operating ranges.",
                remediation=[
                    "Keep Windows and drivers updated.",
                    "Run periodic scans to establish a baseline.",
                    "Review startup apps if boot time or responsiveness changes.",
                ],
            )
        )

    return findings


def _detect_event_log_issues(snapshot: HealthSnapshot) -> list[Finding]:
    text = "\n".join(snapshot.windows_events).lower()
    if not text:
        return []

    findings: list[Finding] = []
    if "windowsupdateclient" in text or "installation failure" in text:
        findings.append(
            Finding(
                code="windows_update_failure",
                title="Recent Windows Update failure detected",
                severity="warning",
                evidence=_matching_events(snapshot, ("windowsupdateclient", "installation failure")),
                likely_cause="An update or Microsoft Store package may be blocked by an app currently in use or a stuck update state.",
                remediation=[
                    "Restart the PC when convenient, then rerun Windows Update.",
                    "Close the app named in the update error before retrying.",
                    "If the same update fails repeatedly, run Windows Update Troubleshooter.",
                ],
            )
        )

    if "explorer.exe" in text and any(term in text for term in ("crash", "stopped working", "faulting")):
        findings.append(
            Finding(
                code="explorer_crash",
                title="Recent Explorer crash signal found",
                severity="warning",
                evidence=_matching_events(snapshot, ("explorer.exe", "faulting", "stopped working")),
                likely_cause="Explorer may have been disrupted by a shell extension, thumbnail handler, or unstable folder view.",
                remediation=[
                    "Restart Windows Explorer from Task Manager if the shell feels frozen.",
                    "Note whether the crash happens when opening a specific folder.",
                    "Disable recently added shell extensions if the crash repeats.",
                ],
            )
        )

    if "clipboard" in text or "clipsvc" in text or "cbdhsvc" in text:
        findings.append(
            Finding(
                code="clipboard_failure",
                title="Clipboard-related issue found in recent logs",
                severity="warning",
                evidence=_matching_events(snapshot, ("clipboard", "clipsvc", "cbdhsvc")),
                likely_cause="Windows clipboard history or a clipboard-dependent app may be stuck.",
                remediation=[
                    "Turn Clipboard History off and back on in Windows Settings.",
                    "Restart Windows Explorer if copy and paste fail across apps.",
                    "Reboot if clipboard failures persist after closing clipboard manager apps.",
                ],
            )
        )

    if "service control manager" in text and any(term in text for term in ("timeout", "failed to start")):
        findings.append(
            Finding(
                code="service_timeout",
                title="Recent Windows service timeout detected",
                severity="warning",
                evidence=_matching_events(snapshot, ("service control manager", "timeout", "failed to start")),
                likely_cause="A background Windows or device service did not respond quickly enough during startup or operation.",
                remediation=[
                    "If the PC is otherwise stable, monitor whether this repeats.",
                    "Restart before troubleshooting further so transient service stalls clear.",
                    "If the same service appears repeatedly, update or reinstall the related driver or app.",
                ],
            )
        )

    return findings


def _matching_events(snapshot: HealthSnapshot, terms: tuple[str, ...], limit: int = 3) -> list[str]:
    matches = [
        event
        for event in snapshot.windows_events
        if any(term in event.lower() for term in terms)
    ]
    return matches[:limit] or ["Matching event was present in the recent Windows event sample."]


def _detect_recurring(history: list[HealthReport]) -> list[Finding]:
    recent = history[-8:]
    if len(recent) < 3:
        return []

    codes = Counter(
        finding.code
        for report in recent
        for finding in report.analysis.findings
        if finding.severity in {"warning", "critical"}
    )
    findings: list[Finding] = []
    for code, count in codes.items():
        if count >= 3:
            findings.append(
                Finding(
                    code=f"recurring_{code}",
                    title=f"Recurring issue: {code.replace('_', ' ')}",
                    severity="warning",
                    evidence=[f"Detected {count} time(s) in the last {len(recent)} saved report(s)."],
                    likely_cause="This looks persistent rather than a one-time workload spike.",
                    remediation=[
                        "Compare the top process list across recent reports.",
                        "Check startup apps and scheduled tasks for related software.",
                        "Address the underlying warning before it becomes normal background noise.",
                    ],
                )
            )
    return findings
