const $ = (id) => document.getElementById(id);
const escapeText = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        ch
      ],
  );
let data,
  local = false,
  health,
  current,
  editing = false,
  busy = false;
let selectedDocument;

function toast(message) {
  $("toast").textContent = message;
  $("toast").classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => $("toast").classList.add("hidden"), 6500);
}
async function api(path, options = {}) {
  const response = await fetch(`./api/${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Check the document and try again.",
    );
  return body;
}
function setBusy(value) {
  busy = value;
  document
    .querySelectorAll(
      "#review-button,#approve-button,#reject-button,#experiment-button",
    )
    .forEach((button) => (button.disabled = value));
  $("review-button").firstChild.textContent = value
    ? "Reviewing… "
    : "Run review ";
}
function profile() {
  return document.querySelector('input[name="profile"]:checked').value;
}
function sourceText() {
  return editing ? $("document-editor").value : selectedDocument.text;
}
function renderSource(highlight = null) {
  const lines = sourceText().split("\n");
  if (lines.at(-1) === "") lines.pop();
  $("line-count").textContent = `${lines.length} lines`;
  $("source-lines").innerHTML = lines
    .map(
      (line, i) =>
        `<div id="line-${i + 1}" class="source-line ${line.startsWith("#") ? "heading" : ""} ${highlight === i + 1 ? "highlighted" : ""}"><span class="line-number">${i + 1}</span><span>${escapeText(line) || " "}</span></div>`,
    )
    .join("");
}
function selectDocument() {
  selectedDocument = data.documents.find(
    (doc) => doc.id === $("document-select").value,
  );
  current = null;
  editing = false;
  $("document-editor").classList.add("hidden");
  $("source-lines").classList.remove("hidden");
  $("edit-toggle").textContent = "Edit document";
  $("source-heading").textContent = selectedDocument.title;
  $("document-description").textContent = selectedDocument.description;
  renderSource();
  renderReview();
}
function renderReview() {
  const status = current?.status || "idle";
  const labels = {
    idle: "Ready to review",
    awaiting_review: "Awaiting your decision",
    published: local ? "Published locally" : "Replay report ready",
    rejected: "Publication rejected",
  };
  $("review-status").className = `status-badge ${status}`;
  $("review-status").textContent = labels[status] || status;
  $("decision-panel").classList.toggle("hidden", !current?.can_decide);
  $("report-actions").classList.toggle("hidden", status !== "published");
  $("decision-mode").textContent = local
    ? "Your decision is stored locally with this run."
    : "Replay only: this decision stays in this browser session.";
  $("trace-list").innerHTML = (current?.trace || [])
    .map(
      (entry) =>
        `<li><strong>${escapeText(entry.step)}</strong><p>${escapeText(entry.detail)}</p></li>`,
    )
    .join("");
  $("trace-count").textContent = `${current?.trace?.length || 0} steps`;
  document.querySelectorAll("#step-list li").forEach((item, index) => {
    item.classList.toggle(
      "done",
      !!current &&
        (index < 3 ||
          (index === 3 && !current.can_decide) ||
          (index === 4 && status === "published")),
    );
    item.classList.toggle("current", !!current?.can_decide && index === 3);
  });
  if (!current) {
    $("review-results").innerHTML =
      '<div class="empty-state"><div class="document-glyph" aria-hidden="true">⌕</div><h3>Let the source speak.</h3><p>Run a review to see evidence-backed findings, the execution trace, and the approval checkpoint.</p><p class="small">Try Atlas with both harness profiles.</p></div>';
    return;
  }
  const findings = current.findings || [];
  const top =
    status === "published"
      ? `<div class="success-note">${local ? "Report published locally." : "Replay complete."} No external message was sent.</div>`
      : status === "rejected"
        ? '<div class="rejected-note">Publication was rejected. The review remains available for inspection.</div>'
        : "";
  $("review-results").innerHTML =
    top +
    `<p class="review-summary">${escapeText(current.raw_review.summary)}</p><div class="findings-stats"><span>${findings.length} findings</span><span>${findings.filter((f) => f.severity === "high").length} high priority</span><span>${escapeText(current.profile_info.name)}</span></div>` +
    findings
      .map(
        (f) =>
          `<article class="finding"><div class="finding-header"><h3>${escapeText(f.title)}</h3><span class="severity ${escapeText(f.severity)}">${escapeText(f.severity)}</span></div><blockquote>${escapeText(f.quote)}</blockquote><p>${escapeText(f.suggestion)}</p><button class="text-button evidence-link" data-line="${Number(f.line)}">Inspect source · line ${Number(f.line)}</button></article>`,
      )
      .join("") +
    (!findings.length
      ? '<div class="finding"><h3>No fixture-rule findings.</h3><p>This is not proof that the document is complete or correct. Review the source before deciding.</p></div>'
      : "") +
    (current.rejected.length
      ? `<div class="withheld">${current.rejected.length} unsupported or duplicate findings withheld. Inspect the downloaded report or API response for details.</div>`
      : "");
  document.querySelectorAll(".evidence-link").forEach((button) =>
    button.addEventListener("click", () => {
      if (editing) $("edit-toggle").click();
      renderSource(Number(button.dataset.line));
      $(`line-${button.dataset.line}`)?.scrollIntoView({
        block: "nearest",
        behavior: "instant",
      });
    }),
  );
}
async function runReview() {
  if (busy) return;
  const document = sourceText();
  if (document.trim().length < 20)
    return toast("Add at least 20 characters of document text.");
  setBusy(true);
  try {
    if (local)
      current = await api("reviews", {
        method: "POST",
        body: JSON.stringify({
          title: selectedDocument.title,
          document,
          profile: profile(),
        }),
      });
    else
      current = structuredClone(
        data.recordings[`${selectedDocument.id}:${profile()}`],
      );
    $("reviewer-note").value = "";
    renderReview();
    await loadHistory();
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(false);
  }
}
async function decide(approved) {
  if (!current?.can_decide || busy) return;
  setBusy(true);
  try {
    if (local)
      current = await api(`reviews/${current.run_id}/decision`, {
        method: "POST",
        body: JSON.stringify({ approved, note: $("reviewer-note").value }),
      });
    else {
      current.can_decide = false;
      current.approved = approved;
      current.status = approved ? "published" : "rejected";
      current.reviewer_note = $("reviewer-note").value;
      current.trace.push({
        step: "Replay decision",
        detail: approved
          ? "Publication simulated in this browser only."
          : "Publication rejected in this browser only.",
      });
    }
    renderReview();
    await loadHistory();
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(false);
  }
}
async function loadHistory() {
  if (!local) return;
  const runs = await api("runs");
  $("history-list").innerHTML = runs.length
    ? runs
        .slice(0, 6)
        .map(
          (run) =>
            `<button data-run="${escapeText(run.id)}">${escapeText(run.title)}<br><span>${escapeText(run.status.replaceAll("_", " "))}</span></button>`,
        )
        .join("")
    : "No reviews yet.";
  document.querySelectorAll("[data-run]").forEach((button) =>
    button.addEventListener("click", async () => {
      try {
        current = await api(`reviews/${button.dataset.run}`);
        selectedDocument = {
          id: "restored",
          title: current.title,
          text: current.document,
        };
        editing = false;
        $("document-editor").classList.add("hidden");
        $("source-lines").classList.remove("hidden");
        $("source-heading").textContent = current.title;
        $("document-description").textContent =
          "Restored from the local SQLite checkpoint.";
        renderSource();
        renderReview();
      } catch (error) {
        toast(error.message);
      }
    }),
  );
}
function renderEvaluation() {
  const evaluation = data.evaluation;
  $("evaluation-results").innerHTML =
    '<div class="metric-grid">' +
    Object.entries(evaluation)
      .map(
        ([key, value]) =>
          `<article class="metric"><h3>${escapeText(data.profiles[key].name)}</h3><div class="metric-row"><span>Rule recall</span><strong>${Math.round(value.recall * 100)}%</strong></div><progress class="bar" aria-label="Rule recall" max="100" value="${Math.round(value.recall * 100)}"></progress><div class="metric-row"><span>Rule precision</span><strong>${Math.round(value.precision * 100)}%</strong></div><p class="small">${value.documents} holdout documents · ${value.false_positive} false positives · ${value.false_negative} missed rules</p></article>`,
      )
      .join("") +
    '</div><table class="result-table"><thead><tr><th scope="col">Held-out document</th><th scope="col">Baseline</th><th scope="col">Evidence-aware</th></tr></thead><tbody>' +
    evaluation.baseline.rows
      .map(
        (row, index) =>
          `<tr><td>${escapeText(data.documents.find((doc) => doc.id === row.id).title)}</td><td class="${row.passed ? "pass" : "fail"}">${row.passed ? "Pass" : "Missed rule"}</td><td class="${evaluation.evidence.rows[index].passed ? "pass" : "fail"}">${evaluation.evidence.rows[index].passed ? "Pass" : "Missed rule"}</td></tr>`,
      )
      .join("") +
    "</tbody></table>";
}
function showExperiment(result, replay = false) {
  $("experiment-results").innerHTML =
    `<div class="experiment-receipt"><h3>${replay ? "Recorded experiment" : "Experiment completed"}</h3><p>${result.outcome.done} development tasks · ${result.executions.length} actual LangGraph executions · ${result.editor_calls} scripted editor calls</p><p class="small">${escapeText(result.note)}</p><details><summary>Inspect the execution receipt</summary><pre>${escapeText(JSON.stringify({ upstream_commit: result.upstream_commit, mode: result.mode, budget: result.budget, outcome: result.outcome, executions: result.executions }, null, 2))}</pre></details></div>`;
}
async function runExperiment() {
  if (busy) return;
  if (!local) {
    showExperiment(data.experiment, true);
    return;
  }
  setBusy(true);
  $("experiment-button").textContent = "Running isolated probes…";
  try {
    showExperiment(
      await api("experiments", {
        method: "POST",
        body: JSON.stringify({ mode: $("experiment-mode").value }),
      }),
    );
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(false);
    $("experiment-button").textContent = "Run Harness² experiment";
  }
}
document.querySelectorAll("[data-view]").forEach((button) =>
  button.addEventListener("click", () => {
    document
      .querySelectorAll(".view")
      .forEach((view) =>
        view.classList.toggle(
          "hidden",
          view.id !== `${button.dataset.view}-view`,
        ),
      );
    document.querySelectorAll("[data-view]").forEach((tab) => {
      tab.classList.toggle("active", tab === button);
      if (tab === button) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    });
  }),
);
$("document-select").addEventListener("change", selectDocument);
document.querySelectorAll("input[name=profile]").forEach((input) =>
  input.addEventListener("change", () => {
    current = null;
    renderReview();
  }),
);
$("review-button").addEventListener("click", runReview);
$("approve-button").addEventListener("click", () => decide(true));
$("reject-button").addEventListener("click", () => decide(false));
$("experiment-button").addEventListener("click", runExperiment);
$("edit-toggle").addEventListener("click", () => {
  if (!local)
    return toast(
      "Custom documents need the local application. This hosted walkthrough uses synthetic recordings.",
    );
  editing = !editing;
  if (editing) $("document-editor").value = selectedDocument.text;
  else selectedDocument.text = $("document-editor").value;
  $("document-editor").classList.toggle("hidden", !editing);
  $("source-lines").classList.toggle("hidden", editing);
  $("edit-toggle").textContent = editing ? "View source" : "Edit document";
  current = null;
  renderSource();
  renderReview();
});
$("download-button").addEventListener("click", async () => {
  try {
    const report = local
      ? await api(`reviews/${current.run_id}/report`)
      : {
          mode: "replay",
          title: current.title,
          findings: current.findings,
          note: current.reviewer_note,
        };
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "tracework-review.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  } catch (error) {
    toast(error.message);
  }
});
async function initialize() {
  try {
    const response = await fetch("./replay.json");
    if (!response.ok) throw new Error("Could not load the demo recordings.");
    data = await response.json();
    try {
      const response = await fetch("./api/health", {
        signal: AbortSignal.timeout(1800),
      });
      if (response.ok) {
        health = await response.json();
        local = health.name === "Tracework" && health.mode === "local";
      }
    } catch {}
    $("mode-banner").textContent = local
      ? `Local application · real LangGraph · ${health.engine === "offline" ? "deterministic offline reviewer" : "local Ollama model"} · SQLite persistence`
      : "Interactive replay · recorded LangGraph runs · no live model or backend · decisions stay in this session";
    $("mode-banner").classList.toggle("live", local);
    $("engine-note").textContent =
      local && health.engine === "ollama"
        ? "Local Ollama reviewer"
        : "Deterministic reviewer · no model calls";
    $("document-select").innerHTML = data.documents
      .map(
        (doc) =>
          `<option value="${escapeText(doc.id)}">${escapeText(doc.title)}${doc.split === "holdout" ? " · holdout" : ""}</option>`,
      )
      .join("");
    if (!local) {
      $("experiment-button").textContent = "Inspect recorded experiment";
      $("experiment-mode").disabled = true;
    }
    selectDocument();
    renderEvaluation();
    if (data.experiment) showExperiment(data.experiment, true);
    await loadHistory();
  } catch (error) {
    $("mode-banner").textContent =
      "The lab could not start. See the error message for details.";
    toast(error.message);
  }
}
initialize();
