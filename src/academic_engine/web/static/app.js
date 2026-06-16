const state = {
  tab: "detect",
  maxWords: 4000,
  lastOutput: "",
  fastConfigured: false,
  remotePolicy: null,
  preset: "quick",
};

const presetMap = {
  quick: {
    detectors: "local",
    execution: "sequential",
    title: "Quick local check",
    copy: "Local stylometry and heuristic signals. Fastest and private to this backend.",
  },
  strong: {
    detectors: "local+fast-detectgpt",
    execution: "sequential",
    title: "Strong check",
    copy: "Local signals plus Fast-DetectGPT when remote scoring is configured.",
  },
  remote: {
    detectors: "official-fast-detectgpt",
    execution: "sequential",
    title: "Remote Fast-DetectGPT",
    copy: "Focused model-based signal. Use when you explicitly want the remote detector path.",
  },
};

const tabs = document.querySelectorAll(".mode-button");
const presetButtons = document.querySelectorAll(".preset-button");
const form = document.querySelector("#form");
const health = document.querySelector("#health");
const fastStatus = document.querySelector("#fast-status");
const statusLine = document.querySelector("#job-status");
const resultTitle = document.querySelector("#result-title");
const recommendation = document.querySelector("#recommendation");
const summary = document.querySelector("#summary");
const result = document.querySelector("#result");
const textInput = document.querySelector("#text");
const wordCount = document.querySelector("#word-count");
const limitCopy = document.querySelector("#limit-copy");
const detectorPreset = document.querySelector("#detectors");
const detectorExecution = document.querySelector("#detector-execution");
const cyclesField = document.querySelector("#cycles-field");
const submit = document.querySelector("#submit");
const submitLabel = document.querySelector("#submit-label");
const copyOutput = document.querySelector("#copy-output");
const contextNote = document.querySelector("#context-note");

function setTab(tab) {
  state.tab = tab;
  tabs.forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  cyclesField.hidden = tab !== "refine";
  submitLabel.textContent = tab === "detect" ? "Run detector check" : "Refine draft";
  statusLine.textContent = tab === "detect" ? "Paste text and choose a check profile." : "Paste text, choose a check profile, then refine.";
  resultTitle.textContent = "Ready for a run";
  summary.innerHTML = "";
  state.lastOutput = "";
  copyOutput.disabled = true;
  recommendation.innerHTML = recommendationCard({
    kicker: tab === "detect" ? "Next action" : "Refinement plan",
    title: tab === "detect" ? "Run a check to get a writing-level recommendation." : "Run refinement to compare before and after risk.",
    copy:
      tab === "detect"
        ? "Results will prioritize risk band, confidence, and practical revision guidance before provider telemetry."
        : "The accepted output will appear as readable prose with score movement and preservation notes.",
    tone: "neutral",
  });
  result.innerHTML = emptyState(
    tab === "detect"
      ? "The report will show the aggregate signal first, then optional advanced detector details."
      : "The refined draft and before/after diagnostic movement will appear here."
  );
  renderContextNote();
}

function setPreset(preset) {
  state.preset = preset;
  presetButtons.forEach((button) => button.classList.toggle("active", button.dataset.preset === preset));
  const config = presetMap[preset];
  detectorPreset.value = config.detectors;
  detectorExecution.value = config.execution;
  renderContextNote();
}

function emptyState(copy) {
  return `<div class="empty-state"><strong>No analysis yet</strong><p>${escapeHtml(copy)}</p></div>`;
}

function updateWordCount() {
  const count = countWords(textInput.value);
  wordCount.textContent = `${count} ${count === 1 ? "word" : "words"}`;
  wordCount.classList.toggle("error", count > state.maxWords);
}

function countWords(value) {
  return value.trim() ? value.trim().split(/\s+/).length : 0;
}

function metric(label, value, hint = "") {
  const display = formatValue(value);
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(display)}</strong>${hint ? `<em>${escapeHtml(hint)}</em>` : ""}</div>`;
}

function formatValue(value) {
  if (typeof value === "number") return value.toFixed(4);
  if (value === null || value === undefined || value === "") return "n/a";
  return String(value).replaceAll("_", " ");
}

function riskBand(risk) {
  if (typeof risk !== "number") return { label: "unknown", tone: "neutral", hint: "insufficient signal" };
  if (risk >= 0.72) return { label: "higher risk", tone: "high", hint: "review before sharing" };
  if (risk >= 0.48) return { label: "mixed risk", tone: "medium", hint: "needs interpretation" };
  return { label: "lower risk", tone: "low", hint: "no strong aggregate flag" };
}

function confidenceBand(summaryData = {}) {
  const disagreement = summaryData.disagreement;
  const unavailable = summaryData.unavailable_count ?? 0;
  if (unavailable > 0 && typeof disagreement === "number" && disagreement > 0.34) {
    return { label: "limited", copy: "Some signals are unavailable and the available detectors disagree." };
  }
  if (typeof disagreement === "number" && disagreement > 0.42) {
    return { label: "mixed", copy: "Detector disagreement is high, so treat the aggregate as directional." };
  }
  if (unavailable > 0) {
    return { label: "partial", copy: "The report is usable, but not every configured detector answered." };
  }
  return { label: "steady", copy: "Signals are available enough for a diagnostic summary." };
}

function recommendationFromDetection(payload) {
  const summaryData = payload.summary || {};
  const band = riskBand(summaryData.risk);
  const confidence = confidenceBand(summaryData);
  const style = payload.style || {};
  const topIssue = topStyleIssue(style, payload.warnings || []);
  const action =
    band.tone === "high"
      ? `Revise for specificity and sentence rhythm; keep citations and claims unchanged.`
      : band.tone === "medium"
        ? `Review the highlighted writing pattern before making broad edits.`
        : `Keep the text stable; only make targeted clarity edits if needed.`;
  return {
    kicker: "Recommendation",
    title: `${capitalize(band.label)} with ${confidence.label} confidence`,
    copy: `${confidence.copy} Main writing signal: ${topIssue}. ${action}`,
    tone: band.tone,
  };
}

function recommendationFromRefine(payload, delta) {
  const accepted = typeof delta === "number" && delta >= 0;
  const stop = formatValue(payload.summary?.stop_reason);
  const preservation = preservationSummary(payload.preservation || {});
  return {
    kicker: accepted ? "Accepted refinement" : "Review required",
    title: accepted ? "The candidate improved or held the detector profile." : "The output needs manual review before use.",
    copy: `Stop reason: ${stop}. ${preservation}`,
    tone: accepted ? "low" : "medium",
  };
}

function topStyleIssue(style, warnings) {
  if (style && typeof style === "object") {
    const entries = Object.entries(style)
      .filter(([, value]) => typeof value === "number")
      .sort((a, b) => Math.abs(Number(b[1])) - Math.abs(Number(a[1])));
    if (entries.length) return formatValue(entries[0][0]);
  }
  if (warnings.length) return warnings[0].replace(/\.$/, "");
  return "no dominant writing-level issue returned";
}

function recommendationCard({ kicker, title, copy, tone }) {
  return `<span class="recommendation-kicker">${escapeHtml(kicker)}</span>
    <strong>${escapeHtml(title)}</strong>
    <p>${escapeHtml(copy)}</p>
    <span class="tone-chip ${escapeHtml(tone)}">${escapeHtml(toneLabel(tone))}</span>`;
}

function toneLabel(tone) {
  if (tone === "high") return "high attention";
  if (tone === "medium") return "review";
  if (tone === "low") return "stable";
  return "pending";
}

function providerDisplayName(name = "") {
  const cleaned = String(name).replace(/^local_/, "").replace(/^official_/, "").replaceAll("_", " ");
  if (cleaned.includes("fast detectgpt")) return "Fast-DetectGPT";
  if (cleaned.includes("gltr")) return "Probability shape";
  if (cleaned.includes("readability")) return "Academic readability";
  if (cleaned.includes("stylometry")) return "Stylometry";
  if (cleaned.includes("heuristic")) return "Local heuristic";
  return capitalize(cleaned || "Detector");
}

function renderDetectors(detectors = []) {
  if (!detectors.length) return '<p class="muted">No detector details returned.</p>';
  return `<div class="detector-list">${detectors
    .map((detector) => {
      const score = detector.score === null || detector.score === undefined ? "n/a" : Number(detector.score).toFixed(4);
      return `<div class="detector-row">
        <div>
          <strong>${escapeHtml(providerDisplayName(detector.provider_name))}</strong>
          <div class="detector-meta">${escapeHtml(formatValue(detector.label))} · score ${escapeHtml(score)} · confidence ${escapeHtml(formatValue(detector.confidence))}</div>
          ${detector.error ? `<div class="error">${escapeHtml(detector.error)}</div>` : ""}
          <code>${escapeHtml(detector.provider_name)}</code>
        </div>
        <span class="badge ${detector.available ? "" : "unavailable"}">${detector.available ? "available" : "unavailable"}</span>
      </div>`;
    })
    .join("")}</div>`;
}

function renderWarnings(warnings = []) {
  if (!warnings.length) return "";
  return `<div class="result-card">
    <strong>Run notes</strong>
    <ul class="warning-list">${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
  </div>`;
}

function renderDetect(payload) {
  const summaryData = payload.summary || {};
  const band = riskBand(summaryData.risk);
  const confidence = confidenceBand(summaryData);
  resultTitle.textContent = "Detector summary";
  recommendation.className = `recommendation-card ${band.tone}`;
  recommendation.innerHTML = recommendationCard(recommendationFromDetection(payload));
  summary.innerHTML =
    metric("Risk band", band.label, band.hint) +
    metric("Risk score", summaryData.risk) +
    metric("Confidence", confidence.label) +
    metric("Signals", `${summaryData.available_count ?? 0}/${(summaryData.available_count ?? 0) + (summaryData.unavailable_count ?? 0)} available`);
  result.innerHTML = `
    <div class="result-card primary-result">
      <strong>What this means</strong>
      <p>${escapeHtml(confidence.copy)} Aggregate consensus: ${escapeHtml(formatValue(summaryData.consensus))}. Disagreement: ${escapeHtml(formatValue(summaryData.disagreement))}.</p>
    </div>
    ${renderWarnings(payload.warnings || [])}
    <details class="advanced-result">
      <summary>Advanced detector details</summary>
      ${renderDetectors(payload.detectors)}
    </details>
  `;
  state.lastOutput = JSON.stringify(payload, null, 2);
  copyOutput.disabled = false;
}

function renderRefine(payload) {
  const beforeRisk = payload.before?.summary?.risk ?? payload.summary?.before_risk;
  const afterRisk = payload.after?.summary?.risk ?? payload.summary?.risk;
  const delta = typeof beforeRisk === "number" && typeof afterRisk === "number" ? beforeRisk - afterRisk : null;
  const afterBand = riskBand(afterRisk);
  resultTitle.textContent = "Refinement result";
  recommendation.className = `recommendation-card ${delta !== null && delta >= 0 ? "low" : "medium"}`;
  recommendation.innerHTML = recommendationCard(recommendationFromRefine(payload, delta));
  summary.innerHTML =
    metric("Before", beforeRisk) +
    metric("After", afterRisk, afterBand.label) +
    metric("Movement", delta, delta === null ? "" : delta >= 0 ? "risk decreased" : "risk increased") +
    metric("Preservation", preservationStatus(payload.preservation || {}));
  result.innerHTML = `
    <div class="text-output">
      <div class="output-head">
        <strong>Refined draft</strong>
        <span>${escapeHtml(afterBand.label)}</span>
      </div>
      <div class="prose-output">${escapeHtml(payload.refined_text || "").replaceAll("\n", "<br />")}</div>
    </div>
    <div class="result-card">
      <strong>Why it was selected</strong>
      <p class="muted">${escapeHtml(formatValue(payload.summary?.stop_reason))}. ${escapeHtml(preservationSummary(payload.preservation || {}))}</p>
    </div>
    ${renderWarnings([...(payload.warnings || []), ...((payload.after && payload.after.warnings) || [])])}
    <details class="advanced-result">
      <summary>Advanced detector details after refinement</summary>
      ${renderDetectors(payload.after?.detectors || [])}
    </details>
  `;
  state.lastOutput = payload.refined_text || JSON.stringify(payload, null, 2);
  copyOutput.disabled = !state.lastOutput;
}

function preservationStatus(preservation) {
  const failures = preservation.hard_constraint_failures || [];
  return failures.length ? "needs review" : "passed";
}

function preservationSummary(preservation) {
  const failures = preservation.hard_constraint_failures || [];
  if (!failures.length) return "No hard preservation failures reported.";
  return `Hard preservation failures: ${failures.join(", ")}`;
}

function renderContextNote() {
  const config = presetMap[state.preset];
  const remoteCopy =
    state.preset === "quick"
      ? "This profile does not request Fast-DetectGPT."
      : state.fastConfigured
        ? remotePolicyCopy()
        : "Fast-DetectGPT is not configured, so remote signals may return unavailable.";
  contextNote.innerHTML = `
    <div>
      <strong>${escapeHtml(config.title)}</strong>
      <p>${escapeHtml(config.copy)}</p>
    </div>
    <div>
      <strong>${state.tab === "detect" ? "Detector mode" : "Refinement mode"}</strong>
      <p>${state.tab === "detect" ? "The app reports diagnostic signal bands and practical writing patterns." : "The app compares before and after diagnostics and rejects non-preserving candidates."}</p>
    </div>
    <div>
      <strong>Remote boundary</strong>
      <p>${escapeHtml(remoteCopy)}</p>
    </div>`;
}

function remotePolicyCopy() {
  const policy = state.remotePolicy || {};
  if (policy.enabled === false) return "Remote detectors are disabled by backend policy.";
  const limit = policy.max_words ? ` Remote limit: ${policy.max_words} words.` : "";
  const used =
    typeof policy.global_daily_used === "number" && typeof policy.daily_limit === "number"
      ? ` Daily budget: ${policy.global_daily_used}/${policy.daily_limit}.`
      : "";
  return `Fast-DetectGPT is configured and controlled by backend cost policy.${limit}${used}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function capitalize(value) {
  const text = String(value).trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

async function pollJob(jobId) {
  for (;;) {
    const response = await fetch(`/api/jobs/${jobId}`);
    const payload = await response.json();
    statusLine.textContent = `${formatValue(payload.kind)} · ${formatValue(payload.status)}`;
    if (payload.status === "failed") {
      resultTitle.textContent = "Run failed";
      result.innerHTML = `<div class="result-card"><strong>Run failed</strong><p class="error">${escapeHtml(payload.error || "Job failed.")}</p></div>`;
      submit.disabled = false;
      return;
    }
    if (payload.status === "succeeded") {
      state.tab === "detect" ? renderDetect(payload.result) : renderRefine(payload.result);
      submit.disabled = false;
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
}

function requestBody() {
  const base = {
    text: textInput.value,
    detectors: detectorPreset.value,
    detector_execution: detectorExecution.value,
  };
  if (state.tab === "detect") return base;
  return {
    ...base,
    cycles: Number(document.querySelector("#cycles").value),
  };
}

tabs.forEach((button) => button.addEventListener("click", () => setTab(button.dataset.tab)));
presetButtons.forEach((button) => button.addEventListener("click", () => setPreset(button.dataset.preset)));
detectorPreset.addEventListener("change", () => {
  const matchingPreset = Object.entries(presetMap).find(([, config]) => config.detectors === detectorPreset.value);
  if (matchingPreset) state.preset = matchingPreset[0];
  presetButtons.forEach((button) => button.classList.toggle("active", button.dataset.preset === state.preset));
  renderContextNote();
});
textInput.addEventListener("input", updateWordCount);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const words = countWords(textInput.value);
  if (!words) {
    resultTitle.textContent = "Missing text";
    result.innerHTML = '<div class="result-card"><strong>Missing text</strong><p class="error">Paste text before running the pipeline.</p></div>';
    return;
  }
  if (words > state.maxWords) {
    resultTitle.textContent = "Input too long";
    result.innerHTML = `<div class="result-card"><strong>Too long</strong><p class="error">This text has ${words} words. The current limit is ${state.maxWords} words.</p></div>`;
    return;
  }
  statusLine.textContent = "Submitting";
  resultTitle.textContent = "Running analysis";
  summary.innerHTML = "";
  recommendation.className = "recommendation-card";
  recommendation.innerHTML = recommendationCard({
    kicker: "Running",
    title: state.preset === "quick" ? "Checking local signals." : "Checking selected detector signals.",
    copy: "Remote Fast-DetectGPT calls can take longer on a cold GPU endpoint.",
    tone: "neutral",
  });
  result.innerHTML = '<div class="empty-state"><strong>Queued</strong><p>The job is running. The report will update automatically.</p></div>';
  state.lastOutput = "";
  copyOutput.disabled = true;
  submit.disabled = true;
  const endpoint = state.tab === "detect" ? "/api/detect" : "/api/refine";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody()),
  });
  const payload = await response.json();
  if (!response.ok) {
    resultTitle.textContent = "Request failed";
    result.innerHTML = `<div class="result-card"><strong>Request failed</strong><p class="error">${escapeHtml(payload.detail || "Request failed.")}</p></div>`;
    statusLine.textContent = "Failed";
    submit.disabled = false;
    return;
  }
  statusLine.textContent = `${formatValue(payload.kind)} · ${formatValue(payload.status)}`;
  if (payload.result || payload.status === "failed") {
    if (payload.status === "failed") {
      resultTitle.textContent = "Run failed";
      result.innerHTML = `<div class="result-card"><strong>Run failed</strong><p class="error">${escapeHtml(payload.error || "Job failed.")}</p></div>`;
    } else {
      state.tab === "detect" ? renderDetect(payload.result) : renderRefine(payload.result);
    }
    submit.disabled = false;
    return;
  }
  await pollJob(payload.job_id);
});

copyOutput.addEventListener("click", async () => {
  if (!state.lastOutput) return;
  await navigator.clipboard.writeText(state.lastOutput);
  copyOutput.textContent = "Copied";
  setTimeout(() => {
    copyOutput.textContent = "Copy";
  }, 1200);
});

fetch("/health")
  .then((response) => response.json())
  .then((payload) => {
    state.maxWords = payload.max_words || state.maxWords;
    state.fastConfigured = Boolean(payload.official_fast_detectgpt?.configured);
    state.remotePolicy = payload.remote_policy || null;
    health.textContent = `Backend ready · ${state.maxWords} words`;
    health.classList.remove("pending", "error");
    fastStatus.textContent = state.fastConfigured
      ? `Fast-DetectGPT ready · ${payload.official_fast_detectgpt.route}`
      : "Fast-DetectGPT not configured";
    fastStatus.classList.toggle("muted", !state.fastConfigured);
    fastStatus.classList.toggle("error", !state.fastConfigured);
    limitCopy.textContent = `Limit ${state.maxWords} words. Quick stays local; Strong and Remote request Fast-DetectGPT only when backend policy allows it.`;
    updateWordCount();
    renderContextNote();
  })
  .catch(() => {
    health.textContent = "Backend unavailable";
    health.classList.remove("pending");
    health.classList.add("error");
  });

setPreset("quick");
setTab("detect");
updateWordCount();
