const scanButton = document.querySelector("#scanButton");
const scanState = document.querySelector("#scanState");
const agentForm = document.querySelector("#agentForm");
const agentInput = document.querySelector("#agentInput");
const agentSend = document.querySelector("#agentSend");
const agentMessages = document.querySelector("#agentMessages");
const LOCAL_AGENT_URL = "http://127.0.0.1:8766";
const isBundledLocalApp =
  ["127.0.0.1", "localhost"].includes(window.location.hostname) && window.location.port === "8765";

async function fetchJson(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(connectionMessage(url));
  }
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function agentCommand(action, parameters = {}, token = "") {
  if (isBundledLocalApp) {
    if (action === "scan") return fetchJson("/api/scan", { method: "POST" });
    if (action === "latest") return fetchJson("/api/latest");
    if (action === "history") return fetchJson("/api/history");
    if (action === "message") {
      return fetchJson("/api/agent/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: parameters.message || "" }),
      });
    }
    if (action === "repair") {
      return fetchJson("/api/agent/repair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_id: parameters.action_id || "", token }),
      });
    }
  }

  const response = await fetchJson(`${LOCAL_AGENT_URL}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, token, parameters }),
  });
  if (response.status === "success") return response.result || {};
  throw new Error(response.message || "Local agent command failed.");
}

function connectionMessage(url) {
  if (String(url).startsWith(LOCAL_AGENT_URL)) {
    return "Cannot reach the LocalMechAI local agent. Start it on this Windows machine with: python local-agent/agent.py, then refresh the dashboard.";
  }
  return "Cannot reach the LocalMechAI local app API. Open the bundled app at http://127.0.0.1:8765 or use the web dashboard with the local agent running on port 8766.";
}

async function loadDashboard() {
  setScanState("Loading", "standby");
  const [latest, history] = await Promise.all([
    agentCommand("latest"),
    agentCommand("history", { limit: 24 }),
  ]);
  renderReport(latest);
  renderHistory(history.reports || []);
  setScanState("Standby", "standby");
}

function renderReport(report) {
  const snapshot = report.snapshot;
  const analysis = report.analysis;
  const findings = analysis.findings || [];
  const worst = getWorstSeverity(findings);

  document.querySelector("#summary").textContent = analysis.summary;
  document.querySelector("#systemState").textContent = labelForSeverity(worst);
  document.querySelector("#lastScan").textContent = formatDate(snapshot.timestamp);
  document.querySelector("#platform").textContent = snapshot.platform;
  document.querySelector("#provider").textContent = analysis.provider;
  document.querySelector("#confidence").textContent = `${Math.round((analysis.confidence || 0) * 100)}% confidence`;
  document.querySelector("#cpu").textContent = `${snapshot.cpu_percent}%`;
  document.querySelector("#memory").textContent = `${snapshot.memory_percent}%`;
  document.querySelector("#swap").textContent = `${snapshot.swap_percent}%`;
  document.querySelector("#cpuCount").textContent = snapshot.cpu_count;
  document.querySelector("#memoryUsed").textContent =
    `${snapshot.memory_used_gb} GB / ${snapshot.memory_total_gb} GB`;
  document.querySelector("#bootTime").textContent = formatDate(snapshot.boot_time);

  setGauge("#cpuGauge", snapshot.cpu_percent);
  setGauge("#memoryGauge", snapshot.memory_percent);
  setGauge("#swapGauge", snapshot.swap_percent);

  renderFindings(findings);
  renderProcesses(snapshot.top_processes || []);
  renderDisks(snapshot.disks || []);
  renderServices(snapshot.services || []);
  renderEvents(snapshot.windows_events || []);
}

function renderFindings(findings) {
  const container = document.querySelector("#findings");
  container.innerHTML = "";
  if (!findings.length) {
    container.appendChild(emptyState("No findings were returned by the scanner."));
    return;
  }

  for (const finding of findings) {
    const element = document.createElement("article");
    element.className = `finding ${finding.severity}`;
    const evidence = (finding.evidence || [])
      .map((item) => `<code>${escapeHtml(item)}</code>`)
      .join("");
    const remediation = (finding.remediation || [])
      .map((step) => `<li>${escapeHtml(step)}</li>`)
      .join("");
    element.innerHTML = `
      <div class="finding-title">
        <h3>${escapeHtml(finding.title)}</h3>
        <span class="severity">${escapeHtml(finding.severity)}</span>
      </div>
      <p>${escapeHtml(finding.likely_cause)}</p>
      ${evidence ? `<div class="evidence"><span>Evidence</span>${evidence}</div>` : ""}
      ${remediation ? `<ol class="steps">${remediation}</ol>` : ""}
    `;
    container.appendChild(element);
  }
}

function renderProcesses(processes) {
  const tbody = document.querySelector("#processes");
  tbody.innerHTML = "";
  if (!processes.length) {
    const row = document.createElement("tr");
    row.innerHTML = `<td colspan="4">No process data returned by the scanner.</td>`;
    tbody.appendChild(row);
    return;
  }

  for (const proc of processes.slice(0, 12)) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(proc.name)} <span class="muted">#${escapeHtml(proc.pid)}</span></td>
      <td>${Number(proc.cpu_percent).toFixed(1)}%</td>
      <td>${Number(proc.memory_mb).toFixed(1)} MB</td>
      <td>${escapeHtml(proc.status)}</td>
    `;
    tbody.appendChild(row);
  }
}

function renderDisks(disks) {
  const container = document.querySelector("#disks");
  container.innerHTML = "";
  if (!disks.length) {
    container.appendChild(emptyState("No disk volumes were available to inspect."));
    return;
  }

  for (const disk of disks) {
    const row = document.createElement("article");
    row.className = "disk-row";
    row.innerHTML = `
      <div class="disk-head">
        <strong>${escapeHtml(disk.mountpoint)}</strong>
        <span>${Number(disk.percent).toFixed(1)}% used</span>
      </div>
      <div class="bar"><span style="width:${clamp(disk.percent, 0, 100)}%"></span></div>
      <p>${disk.free_gb} GB free of ${disk.total_gb} GB</p>
    `;
    container.appendChild(row);
  }
}

function renderServices(services) {
  const container = document.querySelector("#services");
  container.innerHTML = "";
  if (!services.length) {
    container.appendChild(emptyState("Service checks are available on Windows systems."));
    return;
  }

  for (const service of services) {
    const status = String(service.status || "unknown").toLowerCase();
    const card = document.createElement("div");
    card.className = "service-card";
    card.innerHTML = `
      <strong>${escapeHtml(service.name)}</strong>
      <span class="pill ${status === "running" ? "" : "error"}">${escapeHtml(status)}</span>
    `;
    container.appendChild(card);
  }
}

function renderEvents(events) {
  const container = document.querySelector("#events");
  container.innerHTML = "";
  if (!events.length) {
    container.appendChild(emptyState("No recent critical or error events were returned."));
    return;
  }

  for (const event of events.slice(0, 8)) {
    const parts = String(event).split(" | ");
    const item = document.createElement("article");
    item.className = "event";
    item.innerHTML = `
      <strong>${escapeHtml(parts.slice(0, 4).join(" | ") || "Windows event")}</strong>
      <p>${escapeHtml(parts.slice(4).join(" | ") || event)}</p>
    `;
    container.appendChild(item);
  }
}

function renderHistory(reports) {
  document.querySelector("#historyCount").textContent = `${reports.length} reports`;
  const canvas = document.querySelector("#historyChart");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#111517";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  drawGrid(ctx, canvas);

  const recent = reports.slice(-24);
  if (!recent.length) {
    ctx.fillStyle = "#aeb8b8";
    ctx.font = "16px Segoe UI";
    ctx.fillText("No saved reports yet. Run a scan to start the local history.", 34, 132);
    return;
  }

  const points = recent.map((report, index) => ({
    x: 42 + index * ((canvas.width - 78) / Math.max(recent.length - 1, 1)),
    cpu: Number(report.snapshot.cpu_percent || 0),
    memory: Number(report.snapshot.memory_percent || 0),
  }));

  drawLine(ctx, points, "cpu", "#56a6d8");
  drawLine(ctx, points, "memory", "#f2a51a");
  drawLegend(ctx);
}

function addAgentMessage(message, type = "mechanic", actions = []) {
  const element = document.createElement("article");
  element.className = `agent-message ${type}`;
  element.textContent = message;
  if (actions.length) {
    element.appendChild(renderAgentActions(actions));
  }
  agentMessages.appendChild(element);
  agentMessages.scrollTop = agentMessages.scrollHeight;
}

function renderAgentActions(actions) {
  const container = document.createElement("div");
  container.className = "agent-actions";
  for (const action of actions) {
    const card = document.createElement("div");
    card.className = "repair-card";
    const title = document.createElement("strong");
    title.textContent = action.title;
    const description = document.createElement("p");
    description.textContent = action.description;
    const meta = document.createElement("div");
    meta.className = "repair-meta";
    const risk = document.createElement("span");
    risk.textContent = `Risk: ${action.risk}`;
    const confirmation = document.createElement("span");
    confirmation.textContent = "Requires confirmation";
    meta.append(risk, confirmation);

    const button = document.createElement("button");
    button.className = "confirm-repair";
    button.type = "button";
    button.textContent = `Confirm: ${action.title}`;
    button.addEventListener("click", () => confirmRepair(action, button));

    card.append(title, description, meta, button);
    container.appendChild(card);
  }
  return container;
}

async function confirmRepair(action, button) {
  button.disabled = true;
  button.textContent = "Running confirmed action";
  try {
    const result = await agentCommand("repair", { action_id: action.action_id }, action.token);
    addAgentMessage(result.message || "Repair action completed.", result.ok ? "result" : "mechanic");
    if (result.ok) {
      button.textContent = "Confirmed action complete";
      const report = await agentCommand("latest");
      renderReport(report);
    } else {
      button.disabled = false;
      button.textContent = `Retry: ${action.title}`;
    }
  } catch (error) {
    addAgentMessage(error.message, "mechanic");
    button.disabled = false;
    button.textContent = `Retry: ${action.title}`;
  }
}

function setGauge(selector, value) {
  const amount = clamp(Number(value || 0), 0, 100);
  const degrees = amount * 3.6;
  const color = amount >= 90 ? "#ef5d4a" : amount >= 75 ? "#f2a51a" : "#5dd17c";
  document.querySelector(selector).style.background = `
    radial-gradient(circle at center, #15191b 0 49%, transparent 50%),
    conic-gradient(${color} 0deg ${degrees}deg, #3a4247 ${degrees}deg 360deg)
  `;
}

function drawGrid(ctx, canvas) {
  ctx.strokeStyle = "#30383d";
  ctx.lineWidth = 1;
  for (let y = 32; y < canvas.height - 24; y += 42) {
    ctx.beginPath();
    ctx.moveTo(32, y);
    ctx.lineTo(canvas.width - 20, y);
    ctx.stroke();
  }
  for (let x = 42; x < canvas.width - 20; x += 72) {
    ctx.beginPath();
    ctx.moveTo(x, 24);
    ctx.lineTo(x, canvas.height - 30);
    ctx.stroke();
  }
}

function drawLine(ctx, points, key, color) {
  if (!points.length) return;
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  points.forEach((point, index) => {
    const y = 224 - point[key] * 1.85;
    if (index === 0) {
      ctx.moveTo(point.x, y);
    } else {
      ctx.lineTo(point.x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = color;
  for (const point of points) {
    const y = 224 - point[key] * 1.85;
    ctx.beginPath();
    ctx.arc(point.x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawLegend(ctx) {
  ctx.font = "14px Segoe UI";
  ctx.fillStyle = "#56a6d8";
  ctx.fillText("CPU", 38, 24);
  ctx.fillStyle = "#f2a51a";
  ctx.fillText("Memory", 84, 24);
}

function getWorstSeverity(findings) {
  if (findings.some((finding) => finding.severity === "critical")) return "critical";
  if (findings.some((finding) => finding.severity === "warning")) return "warning";
  return "info";
}

function labelForSeverity(severity) {
  if (severity === "critical") return "Critical";
  if (severity === "warning") return "Needs Attention";
  return "Nominal";
}

function setScanState(label) {
  scanState.textContent = label;
}

function emptyState(message) {
  const element = document.createElement("div");
  element.className = "empty";
  element.textContent = message;
  return element;
}

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function clamp(value, min, max) {
  return Math.min(Math.max(Number(value) || 0, min), max);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  scanButton.textContent = "Scanning";
  setScanState("Scanning");
  try {
    const report = await agentCommand("scan");
    renderReport(report);
    const history = await agentCommand("history", { limit: 24 });
    renderHistory(history.reports || []);
    setScanState("Scan Complete");
  } catch (error) {
    setScanState("Scan Error");
    document.querySelector("#summary").textContent = error.message;
  } finally {
    scanButton.disabled = false;
    scanButton.textContent = "Run Live Scan";
  }
});

agentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = agentInput.value.trim();
  if (!message) return;

  addAgentMessage(message, "user");
  agentInput.value = "";
  agentSend.disabled = true;
  agentSend.textContent = "Thinking";
  try {
    const response = await agentCommand("message", { message });
    document.querySelector("#agentProvider").textContent = response.provider || "local-agent";
    addAgentMessage(response.message || "I did not receive an agent response.", "mechanic", response.actions || []);
    if (response.latest_report) {
      renderReport(response.latest_report);
    }
  } catch (error) {
    addAgentMessage(error.message, "mechanic");
  } finally {
    agentSend.disabled = false;
    agentSend.textContent = "Ask Mechanic";
    agentInput.focus();
  }
});

loadDashboard().catch((error) => {
  setScanState("Load Error");
  document.querySelector("#summary").textContent = error.message;
});
