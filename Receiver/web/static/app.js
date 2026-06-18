const POLL_MS = 1000;

const PLOT_ORDER = [
  ["qpsk_接收星座图", "QPSK 接收星座图"],
  ["qdpsk_接收星座图", "QDPSK 接收星座图"],
  ["qdpsk_差分星座图", "QDPSK 差分星座图"],
  ["qpsk_接收眼图", "QPSK 接收眼图"],
  ["qdpsk_接收眼图", "QDPSK 接收眼图"],
  ["接收波形幅度", "接收波形幅度"],
  ["接收相位轨迹", "接收相位轨迹"],
  ["接收功率谱", "接收功率谱"],
  ["误差矢量幅度", "误差矢量幅度"],
];

const TX_PLOT_ORDER = [
  ["tx_qpsk_impaired_constellation", "QPSK 信道后星座图"],
  ["tx_qdpsk_impaired_constellation", "QDPSK 信道后星座图"],
  ["tx_qpsk_impaired_eye", "QPSK 信道后眼图"],
  ["tx_qdpsk_impaired_eye", "QDPSK 信道后眼图"],
  ["tx_qpsk_psd", "QPSK 信道前基带功率谱"],
  ["tx_qdpsk_psd", "QDPSK 信道前基带功率谱"],
  ["tx_qpsk_eye", "QPSK 信道前基带眼图"],
  ["tx_qdpsk_eye", "QDPSK 信道前基带眼图"],
  ["tx_qpsk_constellation", "QPSK 信道前星座图"],
  ["tx_qdpsk_constellation", "QDPSK 信道前星座图"],
];

const state = {
  lastAssetKey: "",
};

document.getElementById("startBtn").addEventListener("click", () => postAction("/api/start"));
document.getElementById("stopBtn").addEventListener("click", () => postAction("/api/stop"));
document.getElementById("analyzeBtn").addEventListener("click", () => postAction("/api/analyze-latest"));
document.getElementById("exportBtn").addEventListener("click", exportLatest);

async function postAction(path) {
  try {
    const response = await fetch(path, { method: "POST", cache: "no-store" });
    const payload = await response.json();
    renderState(payload.state || payload);
  } catch (error) {
    showError(String(error));
  }
}

async function refreshState() {
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    const payload = await response.json();
    renderState(payload);
  } catch (error) {
    showError(String(error));
  }
}

async function exportLatest() {
  try {
    const response = await fetch("/api/export-latest", { method: "POST", cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) {
      renderState(payload.state || {});
      throw new Error(payload.error || response.statusText);
    }
    renderState(payload);
    document.getElementById("lastUpdate").textContent = "导出完成";
  } catch (error) {
    showError(String(error));
  }
}

function renderState(payload) {
  const status = payload.status || "unknown";
  const statusBadge = document.getElementById("statusBadge");
  statusBadge.textContent = status;
  statusBadge.className = `status-badge ${status}`;

  document.getElementById("endpoint").textContent =
    `UDP ${payload.listen_host || "127.0.0.1"}:${payload.listen_port || 9000}`;
  document.getElementById("instanceLine").textContent =
    `实例 ${payload.instance_id || "--"}`;
  document.getElementById("txTargetHint").textContent = payload.tx_target_hint || "--";
  document.getElementById("lanAddresses").textContent =
    (payload.lan_addresses && payload.lan_addresses.length)
      ? payload.lan_addresses.join(" / ")
      : "--";
  document.getElementById("listenBind").textContent =
    `${payload.listen_host || "0.0.0.0"}:${payload.listen_port || 9000}`;
  document.getElementById("referenceStatus").textContent =
    payload.reference_available ? "已接收" : "等待 TX 上传";
  renderTxParams(payload.latest_tx_params || {});
  const referenceImage = document.getElementById("referenceImage");
  if (payload.reference_available) {
    referenceImage.src = withCache("/reference-image");
  } else {
    referenceImage.removeAttribute("src");
  }
  document.getElementById("frameId").textContent = valueOrDash(payload.latest_frame_id);
  document.getElementById("captureDir").textContent = basename(payload.latest_capture_dir) || "--";
  document.getElementById("analysisTime").textContent = formatTime(payload.last_analysis_completed_at);
  document.getElementById("lastUpdate").textContent = `刷新 ${new Date().toLocaleTimeString()}`;
  document.getElementById("firstHeader").textContent = payload.first_header || "等待首个包头";

  renderProgress("qpsk", payload.progress && payload.progress["0"]);
  renderProgress("qdpsk", payload.progress && payload.progress["1"]);
  renderStats(payload.latest_channel_stats || {});
  renderAssets(payload);
  renderError(payload.last_error);
}

function renderTxParams(params) {
  document.getElementById("txSnr").textContent =
    params.snr_db === null || params.snr_db === undefined
      ? "--"
      : `${Number(params.snr_db).toFixed(1)} dB`;
  document.getElementById("txPhase").textContent =
    params.phase_deg === null || params.phase_deg === undefined
      ? "--"
      : `${Number(params.phase_deg).toFixed(0)} deg`;
}

function renderProgress(prefix, progress) {
  const text = document.getElementById(`${prefix}ProgressText`);
  const bar = document.getElementById(`${prefix}ProgressBar`);
  if (!progress) {
    text.textContent = "0 / 0";
    bar.style.width = "0%";
    return;
  }
  const percent = Math.max(0, Math.min(100, Number(progress.percent || 0)));
  text.textContent = `${progress.received_chunks} / ${progress.chunk_count} (${percent.toFixed(1)}%)`;
  bar.style.width = `${percent}%`;
}

function renderStats(stats) {
  const qpsk = stats.qpsk || {};
  const qdpsk = stats.qdpsk || {};
  const rows = [
    ["MSE", fmtNumber(qpsk.mse), fmtNumber(qdpsk.mse)],
    ["PSNR", valueOrDash(qpsk.psnr), valueOrDash(qdpsk.psnr)],
    ["IMG0 Header", headerStatus(qpsk.header_valid), headerStatus(qdpsk.header_valid)],
    ["Samples", valueOrDash(qpsk.sample_count), valueOrDash(qdpsk.sample_count)],
    ["Raw Power", fmtNumber(qpsk.raw_average_power), fmtNumber(qdpsk.raw_average_power)],
    ["Filtered Power", fmtNumber(qpsk.filtered_average_power), fmtNumber(qdpsk.filtered_average_power)],
    ["Symbols", valueOrDash(qpsk.symbol_sample_count), valueOrDash(qdpsk.symbol_sample_count)],
    ["Symbol Power", fmtNumber(qpsk.symbol_average_power), fmtNumber(qdpsk.symbol_average_power)],
  ];
  document.getElementById("statsBody").innerHTML = rows
    .map(([name, left, right]) => `<tr><td>${name}</td><td>${left}</td><td>${right}</td></tr>`)
    .join("");

  document.getElementById("qpskQuality").textContent =
    `MSE ${fmtNumber(qpsk.mse)} / PSNR ${valueOrDash(qpsk.psnr)}`;
  document.getElementById("qdpskQuality").textContent =
    `MSE ${fmtNumber(qdpsk.mse)} / PSNR ${valueOrDash(qdpsk.psnr)}`;
}

function renderAssets(payload) {
  const assets = payload.latest_asset_urls || {};
  const assetKey = JSON.stringify(assets);
  if (assetKey === state.lastAssetKey) {
    return;
  }
  state.lastAssetKey = assetKey;

  setImage("qpskImage", assets.qpsk_recovered);
  setImage("qdpskImage", assets.qdpsk_recovered);
  if (assets.report) {
    document.getElementById("reportLink").href = assets.report;
  }
  const plotGrid = document.getElementById("plotGrid");
  plotGrid.innerHTML = "";
  for (const [key, title] of PLOT_ORDER) {
    const url = assets[key];
    const figure = document.createElement("figure");
    figure.innerHTML = `<figcaption>${title}<span>Matplotlib</span></figcaption><img alt="${title}">`;
    const img = figure.querySelector("img");
    if (url) {
      img.src = withCache(url);
    }
    plotGrid.appendChild(figure);
  }
  renderTxPlots(assets);
}

function renderTxPlots(assets) {
  const plotGrid = document.getElementById("txPlotGrid");
  plotGrid.innerHTML = "";
  for (const [key, title] of TX_PLOT_ORDER) {
    const url = assets[key];
    const figure = document.createElement("figure");
    figure.innerHTML = `<figcaption>${title}<span>Transmitter</span></figcaption><img alt="${title}">`;
    const img = figure.querySelector("img");
    if (url) {
      img.src = withCache(url);
    }
    plotGrid.appendChild(figure);
  }
}

function setImage(id, url) {
  const image = document.getElementById(id);
  if (!url) {
    image.removeAttribute("src");
    return;
  }
  image.src = withCache(url);
}

function renderError(errorText) {
  const box = document.getElementById("errorBox");
  if (!errorText) {
    box.hidden = true;
    box.textContent = "";
    return;
  }
  box.hidden = false;
  box.textContent = errorText;
}

function withCache(url) {
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}t=${Date.now()}`;
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "--" : String(value);
}

function fmtNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return Number(value).toFixed(6);
}

function headerStatus(value) {
  if (value === true) {
    return '<span class="ok">valid</span>';
  }
  if (value === false) {
    return '<span class="warn">fallback</span>';
  }
  return "--";
}

function formatTime(value) {
  if (!value) {
    return "--";
  }
  return new Date(Number(value) * 1000).toLocaleTimeString();
}

function basename(path) {
  if (!path) {
    return "";
  }
  return String(path).split(/[\\/]/).filter(Boolean).pop();
}

refreshState();
setInterval(refreshState, POLL_MS);
