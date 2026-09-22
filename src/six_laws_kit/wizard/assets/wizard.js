"use strict";

/* The controller: the step machine, the HTTP client, and the six step transitions.
   Everything that builds DOM lives in wizard2.js, which the page loads right after this file;
   every call into it happens inside an event or poll callback, never at load time. */

/* Step machine ------------------------------------------------------- */
var STEPS = ["welcome", "scan", "heads", "review", "install", "done"];
var state = { dryRun: false, trees: [], skippedRoots: [], selectedTrees: [] };
var headsStart = {}; // path -> ms timestamp, for a client-side elapsed clock
function showStep(name) {
  STEPS.forEach(function (s) {
    var section = document.querySelector('section[data-step="' + s + '"]');
    if (section) section.hidden = s !== name;
    var item = document.querySelector('.step[data-step-item="' + s + '"]');
    if (!item) return;
    item.classList.remove("step-done");
    item.removeAttribute("aria-current");
    if (s === name) item.setAttribute("aria-current", "step");
    else if (STEPS.indexOf(s) < STEPS.indexOf(name)) item.classList.add("step-done");
  });
}

/* Fetch wrapper -------------------------------------------------------
   Every /api/* call carries the per-run token issued by the server. */
function kitFetch(path, opts) {
  opts = opts || {};
  var headers = opts.headers || {};
  headers["X-Kit-Token"] = window.KIT_TOKEN;
  if (opts.body) headers["Content-Type"] = "application/json";
  return fetch(path, {
    method: opts.method || "GET",
    headers: headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  }).then(function (r) {
    if (r.status === 204 || r.status === 202) return {};
    return r.json().catch(function () { return {}; });
  });
}
var api = {
  state: function () { return kitFetch("/api/state"); },
  scanStart: function () { return kitFetch("/api/scan", { method: "POST" }); },
  scanProgress: function () { return kitFetch("/api/scan"); },
  setSelection: function (selected) {
    return kitFetch("/api/selection", { method: "POST", body: { selected: selected } });
  },
  headsStart: function () { return kitFetch("/api/heads", { method: "POST" }); },
  headsProgress: function () { return kitFetch("/api/heads"); },
  plan: function () { return kitFetch("/api/plan"); },
  installStart: function () {
    return kitFetch("/api/install", { method: "POST", body: { confirm: true } });
  },
  installProgress: function () { return kitFetch("/api/install"); },
  done: function () { return kitFetch("/api/done"); },
  quit: function () { return kitFetch("/api/quit", { method: "POST" }); },
};

/* Polling helper: fixed interval, stops itself when `done(payload)` is true */
function poll(fn, intervalMs, done, onTick) {
  var timer = setInterval(function () {
    fn().then(function (payload) {
      onTick(payload);
      if (done(payload)) clearInterval(timer);
    });
  }, intervalMs);
  return timer;
}

/* Welcome -> Scan ------------------------------------------------------ */
document.getElementById("btn-start").addEventListener("click", function () {
  showStep("scan");
  api.scanStart().then(function () {
    poll(api.scanProgress, 400, function (p) { return p.done; }, onScanTick);
  });
});
function onScanTick(p) {
  var counter = document.getElementById("scan-counter");
  state.skippedRoots = p.skipped_roots || [];
  if (!p.done) {
    counter.textContent = "Scanning… " + (p.dirs_seen || 0) + " directories checked.";
    return;
  }
  counter.textContent = p.dirs_seen ? "Scan complete: " + p.dirs_seen + " directories checked." : "Scan complete.";
  api.state().then(function (s) {
    state.dryRun = !!s.dry_run;
    state.trees = s.trees || [];
    renderForest(state.trees);
    renderSkipped(state.skippedRoots);
    document.getElementById("scan-results").hidden = false;
    document.getElementById("btn-scan-next").disabled = state.trees.length === 0;
  });
}

/* Scan -> Heads -------------------------------------------------------- */
document.getElementById("btn-scan-next").addEventListener("click", function () {
  var selected = Array.prototype.map.call(
    document.querySelectorAll("#tree-root input[type=checkbox]:checked"),
    function (el) { return el.dataset.path; }
  );
  state.selectedTrees = state.trees.filter(function (t) {
    return selected.indexOf(t.path) !== -1;
  });
  api.setSelection(selected).then(function () {
    showStep("heads");
    renderHeadsRows(state.selectedTrees);
    api.headsStart().then(function () {
      poll(api.headsProgress, 700, function (p) { return p.done; }, onHeadsTick);
    });
  });
});
function onHeadsTick(p) {
  (p.results || []).forEach(function (row) {
    var tr = document.querySelector('#heads-tbody tr[data-path="' + cssEscape(row.path) + '"]');
    if (!tr) {
      tr = headsRow({ path: row.path, name: row.path.split("/").pop() || row.path, depth: 0 });
      document.getElementById("heads-tbody").appendChild(tr);
    }
    var badge = tr.querySelector('[data-role="badge"]');
    badge.textContent = row.status;
    badge.className = "badge badge-" + row.status;
    var started = headsStart[row.path] || Date.now();
    var seconds = row.seconds || (Date.now() - started) / 1000;
    tr.querySelector('[data-role="elapsed"]').textContent = seconds.toFixed(1) + "s";
  });
  if (p.done) document.getElementById("btn-heads-next").disabled = false;
}

/* Heads -> Review ------------------------------------------------------------ */
document.getElementById("btn-heads-next").addEventListener("click", function () {
  showStep("review");
  api.plan().then(renderReview);
});

/* Review -> Install ------------------------------------------------------------ */
document.getElementById("btn-confirm").addEventListener("click", function () {
  showStep("install");
  if (state.dryRun) {
    document.getElementById("install-progress-wrap").hidden = true;
    document.getElementById("install-dry-run-note").hidden = false;
    document.getElementById("btn-install-close").hidden = false;
    return;
  }
  api.installStart().then(function () {
    poll(api.installProgress, 300, function (p) { return p.done; }, onInstallTick);
  });
});
function onInstallTick(p) {
  var total = p.total || 1;
  var completed = p.completed || 0;
  document.getElementById("progress-fill").style.width = Math.round((completed / total) * 100) + "%";
  document.getElementById("install-current").textContent = p.current || "Working…";
  if (p.done) {
    api.done().then(renderDone);
    showStep("done");
  }
}
document.getElementById("btn-install-close").addEventListener("click", function () {
  api.quit();
});

/* Done ---------------------------------------------------------------------------- */
function renderDone(d) {
  document.getElementById("done-counts").textContent =
    d.self_rows + " project(s) answered for themselves; " + d.installer_rows + " used a fallback.";
  document.getElementById("done-manifest").textContent = "Manifest written to " + d.manifest_path;
  document.getElementById("paste-text").value = d.paste_block || "";
  document.getElementById("uninstall-cmd").textContent = d.uninstall_cmd || "";
}
document.getElementById("btn-copy").addEventListener("click", function () {
  var text = document.getElementById("paste-text").value;
  var status = document.getElementById("copy-status");
  var mark = function () { status.textContent = "Copied."; setTimeout(function () { status.textContent = ""; }, 2000); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(mark, function () { fallbackCopy(text, mark); });
  } else {
    fallbackCopy(text, mark);
  }
});
function fallbackCopy(text, done) {
  var ta = document.getElementById("paste-text");
  ta.focus();
  ta.select();
  try { document.execCommand("copy"); done(); } catch (e) { /* clipboard unavailable; text stays selected */ }
}
document.getElementById("btn-close").addEventListener("click", function () {
  api.quit();
});

/* Tell the server the wizard is gone even on a hard tab close.
   sendBeacon cannot set a header, so the token rides in the body instead. */
window.addEventListener("pagehide", function () {
  var body = new Blob([JSON.stringify({ token: window.KIT_TOKEN })], { type: "application/json" });
  navigator.sendBeacon("/api/quit", body);
});
showStep("welcome");
