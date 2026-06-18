const elements = {
  statusLine: document.getElementById("status-line"),
  target: document.getElementById("target"),
  imageMeta: document.getElementById("image-meta"),
  sourceImage: document.getElementById("source-image"),
  referencePushStatus: document.getElementById("reference-push-status"),
  targetHost: document.getElementById("target-host"),
  targetPort: document.getElementById("target-port"),
  snr: document.getElementById("snr"),
  snrValue: document.getElementById("snr-value"),
  phase: document.getElementById("phase"),
  phaseValue: document.getElementById("phase-value"),
  renderButton: document.getElementById("render-button"),
  sendButton: document.getElementById("send-button"),
  phasePresets: Array.from(document.querySelectorAll("[data-phase]")),
  generatedAt: document.getElementById("generated-at"),
  qpskSymbols: document.getElementById("qpsk-symbols"),
  qdpskSymbols: document.getElementById("qdpsk-symbols"),
  qpskPackets: document.getElementById("qpsk-packets"),
  qdpskPackets: document.getElementById("qdpsk-packets"),
  txBytes: document.getElementById("tx-bytes"),
  txElapsed: document.getElementById("tx-elapsed"),
  qpskSnr: document.getElementById("qpsk-snr"),
  qdpskSnr: document.getElementById("qdpsk-snr"),
  frameBytes: document.getElementById("frame-bytes"),
  bitCount: document.getElementById("bit-count"),
  qpskSamples: document.getElementById("qpsk-samples"),
  qdpskSamples: document.getElementById("qdpsk-samples"),
  frameId: document.getElementById("frame-id"),
  phaseStat: document.getElementById("phase-stat"),
  qpskPsdCount: document.getElementById("qpsk-psd-count"),
  qdpskPsdCount: document.getElementById("qdpsk-psd-count"),
  qpskEyeCount: document.getElementById("qpsk-eye-count"),
  qdpskEyeCount: document.getElementById("qdpsk-eye-count"),
  qpskConstellationCount: document.getElementById("qpsk-constellation-count"),
  qdpskConstellationCount: document.getElementById("qdpsk-constellation-count"),
  qpskImpairedConstellationCount: document.getElementById("qpsk-impaired-constellation-count"),
  qdpskImpairedConstellationCount: document.getElementById("qdpsk-impaired-constellation-count"),
  qpskImpairedEyeCount: document.getElementById("qpsk-impaired-eye-count"),
  qdpskImpairedEyeCount: document.getElementById("qdpsk-impaired-eye-count"),
  qpskPsdPlot: document.getElementById("qpsk-psd-plot"),
  qdpskPsdPlot: document.getElementById("qdpsk-psd-plot"),
  qpskEyePlot: document.getElementById("qpsk-eye-plot"),
  qdpskEyePlot: document.getElementById("qdpsk-eye-plot"),
  qpskConstellationPlot: document.getElementById("qpsk-constellation-plot"),
  qdpskConstellationPlot: document.getElementById("qdpsk-constellation-plot"),
  qpskImpairedConstellationPlot: document.getElementById("qpsk-impaired-constellation-plot"),
  qdpskImpairedConstellationPlot: document.getElementById("qdpsk-impaired-constellation-plot"),
  qpskImpairedEyePlot: document.getElementById("qpsk-impaired-eye-plot"),
  qdpskImpairedEyePlot: document.getElementById("qdpsk-impaired-eye-plot"),
  channelPlots: Array.from(document.querySelectorAll(".channel-plot")),
};

function formatNumber(value) {
  return Number(value).toLocaleString("en-US");
}

function setBusy(isBusy) {
  elements.renderButton.disabled = isBusy;
  elements.sendButton.disabled = isBusy;
  for (const button of elements.phasePresets) {
    button.disabled = isBusy;
  }
  elements.snr.disabled = isBusy;
  elements.phase.disabled = isBusy;
  elements.targetHost.disabled = isBusy;
  elements.targetPort.disabled = isBusy;
}

function clamp(value, minValue, maxValue) {
  return Math.min(Math.max(Number(value), Number(minValue)), Number(maxValue));
}

async function requestJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (error) {
    throw new Error(`无法连接 TX 后端。请确认页面地址是 http://127.0.0.1:8000，而不是本地 HTML 文件。${error.message}`);
  }
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(text || response.statusText);
  }
  if (!response.ok) {
    throw new Error(payload.error || response.statusText);
  }
  return payload;
}

async function updateConfig() {
  elements.snr.value = clamp(elements.snr.value, elements.snr.min, elements.snr.max);
  elements.phase.value = clamp(elements.phase.value, elements.phase.min, elements.phase.max);
  elements.snrValue.value = `${Number(elements.snr.value).toFixed(1)} dB`;
  elements.phaseValue.value = `${Number(elements.phase.value).toFixed(0)} deg`;
  return requestJson("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      snr_db: Number(elements.snr.value),
      phase_deg: Number(elements.phase.value),
      target_host: elements.targetHost.value,
      target_port: Number(elements.targetPort.value),
    }),
  });
}

function applyState(state) {
  const config = state.config;
  const result = state.result;
  elements.target.textContent = `${config.target_host}:${config.target_port}`;
  elements.targetHost.value = config.target_host;
  elements.targetPort.value = config.target_port;
  elements.snr.value = config.snr_db;
  elements.phase.value = config.phase_deg;
  elements.snrValue.value = `${Number(config.snr_db).toFixed(1)} dB`;
  elements.phaseValue.value = `${Number(config.phase_deg).toFixed(0)} deg`;
  renderReceiverPushStatus(state.reference_push, state.tx_plot_push);
  const image = result.image;
  const modulation = result.modulation;
  const rrc = result.rrc;
  const plots = result.plots;
  const qpskPlots = plots.qpsk;
  const qdpskPlots = plots.qdpsk;
  const udp = result.udp;
  const sendResult = udp.send_result;

  elements.statusLine.textContent = sendResult.sent
    ? `Last UDP send: ${result.generated_at}, ${formatNumber(sendResult.packet_count)} packets`
    : `Last render: ${result.generated_at}`;
  elements.imageMeta.textContent = `${image.width}x${image.height} RGB`;
  elements.generatedAt.textContent = result.generated_at;

  if (state.source_image_url) {
    elements.sourceImage.src = `${state.source_image_url}?t=${Date.now()}`;
  }

  elements.qpskSymbols.textContent = formatNumber(modulation.qpsk_symbol_count);
  elements.qdpskSymbols.textContent = formatNumber(modulation.qdpsk_symbol_count);
  elements.qpskPackets.textContent = formatNumber(udp.qpsk_packet_count);
  elements.qdpskPackets.textContent = formatNumber(udp.qdpsk_packet_count);
  elements.txBytes.textContent = formatNumber(sendResult.total_bytes);
  elements.txElapsed.textContent = `${Number(sendResult.elapsed_sec).toFixed(3)} s`;
  elements.qpskSnr.textContent = `${Number(result.channel.qpsk_estimated_snr_db).toFixed(2)} dB`;
  elements.qdpskSnr.textContent = `${Number(result.channel.qdpsk_estimated_snr_db).toFixed(2)} dB`;
  elements.frameBytes.textContent = formatNumber(image.frame_bytes);
  elements.bitCount.textContent = formatNumber(image.bit_count);
  elements.qpskSamples.textContent = formatNumber(rrc.qpsk_waveform_sample_count);
  elements.qdpskSamples.textContent = formatNumber(rrc.qdpsk_waveform_sample_count);
  elements.frameId.textContent = formatNumber(udp.frame_id);
  elements.phaseStat.textContent = `${Number(result.channel.phase_deg).toFixed(0)} deg`;

  elements.qpskPsdCount.textContent = `${formatNumber(qpskPlots.psd_bins)} bins`;
  elements.qdpskPsdCount.textContent = `${formatNumber(qdpskPlots.psd_bins)} bins`;
  elements.qpskEyeCount.textContent = `${qpskPlots.eye_trace_count} traces`;
  elements.qdpskEyeCount.textContent = `${qdpskPlots.eye_trace_count} traces`;
  elements.qpskConstellationCount.textContent = `${formatNumber(qpskPlots.constellation_plotted_points)} points`;
  elements.qdpskConstellationCount.textContent = `${formatNumber(qdpskPlots.constellation_plotted_points)} points`;
  const hasChannelPlots = Boolean(sendResult.sent);
  elements.qpskImpairedConstellationCount.textContent = hasChannelPlots ? `${formatNumber(qpskPlots.impaired_constellation_points)} points` : "--";
  elements.qdpskImpairedConstellationCount.textContent = hasChannelPlots ? `${formatNumber(qdpskPlots.impaired_constellation_points)} points` : "--";
  elements.qpskImpairedEyeCount.textContent = hasChannelPlots ? `${qpskPlots.impaired_eye_trace_count} traces` : "--";
  elements.qdpskImpairedEyeCount.textContent = hasChannelPlots ? `${qdpskPlots.impaired_eye_trace_count} traces` : "--";

  elements.qpskPsdPlot.src = state.plots.qpsk.psd;
  elements.qdpskPsdPlot.src = state.plots.qdpsk.psd;
  elements.qpskEyePlot.src = state.plots.qpsk.eye;
  elements.qdpskEyePlot.src = state.plots.qdpsk.eye;
  elements.qpskConstellationPlot.src = state.plots.qpsk.constellation;
  elements.qdpskConstellationPlot.src = state.plots.qdpsk.constellation;
  for (const panel of elements.channelPlots) {
    panel.classList.toggle("pending", !hasChannelPlots);
  }
  if (hasChannelPlots) {
    elements.qpskImpairedConstellationPlot.src = state.plots.qpsk.impaired_constellation;
    elements.qdpskImpairedConstellationPlot.src = state.plots.qdpsk.impaired_constellation;
    elements.qpskImpairedEyePlot.src = state.plots.qpsk.impaired_eye;
    elements.qdpskImpairedEyePlot.src = state.plots.qdpsk.impaired_eye;
  } else {
    elements.qpskImpairedConstellationPlot.removeAttribute("src");
    elements.qdpskImpairedConstellationPlot.removeAttribute("src");
    elements.qpskImpairedEyePlot.removeAttribute("src");
    elements.qdpskImpairedEyePlot.removeAttribute("src");
  }
}

function clearResultView() {
  elements.imageMeta.textContent = "--";
  elements.sourceImage.removeAttribute("src");
  for (const item of [
    elements.generatedAt, elements.qpskSymbols, elements.qdpskSymbols,
    elements.qpskPackets, elements.qdpskPackets, elements.txBytes, elements.txElapsed,
    elements.qpskSnr, elements.qdpskSnr, elements.frameBytes, elements.bitCount,
    elements.qpskSamples, elements.qdpskSamples, elements.frameId, elements.phaseStat,
    elements.qpskPsdCount, elements.qdpskPsdCount, elements.qpskEyeCount,
    elements.qdpskEyeCount, elements.qpskConstellationCount, elements.qdpskConstellationCount,
    elements.qpskImpairedConstellationCount, elements.qdpskImpairedConstellationCount,
    elements.qpskImpairedEyeCount, elements.qdpskImpairedEyeCount,
  ]) {
    item.textContent = "--";
  }
  for (const image of [
    elements.qpskPsdPlot, elements.qdpskPsdPlot, elements.qpskEyePlot,
    elements.qdpskEyePlot, elements.qpskConstellationPlot, elements.qdpskConstellationPlot,
    elements.qpskImpairedConstellationPlot, elements.qdpskImpairedConstellationPlot,
    elements.qpskImpairedEyePlot, elements.qdpskImpairedEyePlot,
  ]) {
    image.removeAttribute("src");
  }
  for (const panel of elements.channelPlots) {
    panel.classList.add("pending");
  }
}

function renderReceiverPushStatus(referencePush, txPlotPush) {
  if (!referencePush && !txPlotPush) {
    elements.referencePushStatus.textContent = "发送时同步参考图和发端图到 RX";
    return;
  }
  const referenceText = referencePush && referencePush.ok
    ? "参考图已发送"
    : `参考图失败：${(referencePush && (referencePush.error || referencePush.status)) || "unknown"}`;
  const txPlotText = txPlotPush && txPlotPush.ok
    ? "发端图已发送"
    : `发端图失败：${(txPlotPush && (txPlotPush.error || txPlotPush.status)) || "unknown"}`;
  elements.referencePushStatus.textContent = `${referenceText}；${txPlotText}`;
}

async function refreshState() {
  const state = await requestJson("/api/state");
  applyState(state);
}

async function renderPlots() {
  setBusy(true);
  elements.statusLine.textContent = "Rendering";
  try {
    await updateConfig();
    const state = await requestJson("/api/render", { method: "POST" });
    applyState(state);
  } catch (error) {
    elements.statusLine.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function sendUdp() {
  setBusy(true);
  elements.statusLine.textContent = "Sending UDP";
  try {
    await updateConfig();
    const state = await requestJson("/api/send", { method: "POST" });
    applyState(state);
  } catch (error) {
    elements.statusLine.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

elements.snr.addEventListener("change", () => {
  updateConfig().catch((error) => {
    elements.statusLine.textContent = error.message;
  });
});
elements.phase.addEventListener("change", () => {
  updateConfig().catch((error) => {
    elements.statusLine.textContent = error.message;
  });
});
elements.targetHost.addEventListener("change", () => {
  updateConfig().catch((error) => {
    elements.statusLine.textContent = error.message;
  });
});
elements.targetPort.addEventListener("change", () => {
  updateConfig().catch((error) => {
    elements.statusLine.textContent = error.message;
  });
});
elements.snr.addEventListener("input", () => {
  elements.snrValue.value = `${Number(elements.snr.value).toFixed(1)} dB`;
});
elements.phase.addEventListener("input", () => {
  elements.phaseValue.value = `${Number(elements.phase.value).toFixed(0)} deg`;
});
for (const button of elements.phasePresets) {
  button.addEventListener("click", () => {
    elements.phase.value = clamp(button.dataset.phase, elements.phase.min, elements.phase.max);
    elements.phaseValue.value = `${Number(elements.phase.value).toFixed(0)} deg`;
    updateConfig().catch((error) => {
      elements.statusLine.textContent = error.message;
    });
  });
}
elements.renderButton.addEventListener("click", renderPlots);
elements.sendButton.addEventListener("click", sendUdp);

refreshState().catch((error) => {
  elements.statusLine.textContent = error.message;
});
