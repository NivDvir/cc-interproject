"use strict";

/* Step machine ------------------------------------------------------- */
var STEPS = ["welcome", "scan", "modules", "heads", "review", "install", "done"];
var state = { dryRun: false, sameHooks: [], trees: [], skippedRoots: [] };
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
  setModules: function (modules) {
    return kitFetch("/api/modules", { method: "POST", body: { modules: modules } });
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
    counter.textContent = "Scanning\u2026 " + (p.dirs_seen || 0) + " directories checked.";
    return;
  }
  counter.textContent = "Scan complete: " + (p.dirs_seen || 0) + " directories checked.";
  api.state().then(function (s) {
    state.dryRun = !!s.dry_run;
    state.trees = s.trees || [];
    renderForest(state.trees);
    renderSkipped(state.skippedRoots);
    document.getElementById("scan-results").hidden = false;
    document.getElementById("btn-scan-next").disabled = state.trees.length === 0;
  });
}

function renderForest(trees) {
  var root = document.getElementById("tree-root");
  root.innerHTML = "";
  trees.forEach(function (tree) { root.appendChild(renderTreeItem(tree, true)); });
}

function renderTreeItem(tree, isTop) {
  var li = document.createElement("li");
  if (!isTop) li.className = "inherited";
  var label = document.createElement("label");
  if (isTop) {
    var box = document.createElement("input");
    box.type = "checkbox";
    box.checked = true;
    box.dataset.path = tree.path;
    label.appendChild(box);
  }
  var name = document.createElement("span");
  name.className = "tree-name";
  name.textContent = tree.name;
  label.appendChild(name);
  var date = document.createElement("span");
  date.className = "tree-date";
  date.textContent = tree.has_session ? "last session " + tree.last_session : "no prior session";
  label.appendChild(date);
  li.appendChild(label);
  if (tree.subtrees && tree.subtrees.length) {
    var ul = document.createElement("ul");
    tree.subtrees.forEach(function (sub) { ul.appendChild(renderTreeItem(sub, false)); });
    li.appendChild(ul);
  }
  return li;
}

function renderSkipped(roots) {
  var wrap = document.getElementById("skipped-wrap");
  var list = document.getElementById("skipped-list");
  list.innerHTML = "";
  if (!roots || !roots.length) { wrap.hidden = true; return; }
  roots.forEach(function (r) {
    var li = document.createElement("li");
    li.textContent = r;
    list.appendChild(li);
  });
  wrap.hidden = false;
}

/* Scan -> Modules -------------------------------------------------------- */
document.getElementById("btn-scan-next").addEventListener("click", function () {
  var selected = Array.prototype.map.call(
    document.querySelectorAll("#tree-root input[type=checkbox]:checked"),
    function (el) { return el.dataset.path; }
  );
  api.setSelection(selected).then(function () {
    return api.state();
  }).then(function (s) {
    state.sameHooks = s.same_purpose_hooks || [];
    var routing = document.getElementById("mod-routing");
    var note = document.getElementById("modules-conflict-note");
    if (state.sameHooks.length) {
      routing.checked = false;
      note.hidden = false;
      note.textContent = "Routing hooks already present: " + state.sameHooks.join(", ") + ". Left unchecked.";
    } else {
      note.hidden = true;
    }
    showStep("modules");
  });
});

/* Modules -> Heads --------------------------------------------------------- */
document.getElementById("btn-modules-next").addEventListener("click", function () {
  var modules = ["laws"];
  if (document.getElementById("mod-routing").checked) modules.push("routing");
  api.setModules(modules).then(function () {
    showStep("heads");
    renderHeadsRows(state.trees.filter(function (t) {
      return document.querySelector('#tree-root input[data-path="' + cssEscape(t.path) + '"]:checked');
    }));
    api.headsStart().then(function () {
      poll(api.headsProgress, 700, function (p) { return p.done; }, onHeadsTick);
    });
  });
});

function cssEscape(s) { return s.replace(/["\\]/g, "\\$&"); }

function renderHeadsRows(trees) {
  var body = document.getElementById("heads-tbody");
  body.innerHTML = "";
  trees.forEach(function (t) {
    headsStart[t.path] = Date.now();
    var tr = document.createElement("tr");
    tr.dataset.path = t.path;
    tr.innerHTML =
      '<td>' + t.name + '</td>' +
      '<td><span class="badge badge-waiting" data-role="badge">waiting</span></td>' +
      '<td data-role="elapsed">0.0s</td>';
    body.appendChild(tr);
  });
}

function onHeadsTick(p) {
  (p.results || []).forEach(function (row) {
    var tr = document.querySelector('#heads-tbody tr[data-path="' + cssEscape(row.path) + '"]');
    if (!tr) return;
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

function renderReview(data) {
  var warnings = document.getElementById("review-warnings");
  warnings.innerHTML = "";
  if (data.warnings && data.warnings.length) {
    data.warnings.forEach(function (w) {
      var li = document.createElement("li");
      li.textContent = w;
      warnings.appendChild(li);
    });
    warnings.hidden = false;
  } else {
    warnings.hidden = true;
  }
  var list = document.getElementById("review-actions");
  list.innerHTML = "";
  (data.actions || []).forEach(function (action) {
    var li = document.createElement("li");
    var details = document.createElement("details");
    var summary = document.createElement("summary");
    summary.innerHTML =
      '<span class="action-kind">' + action.kind + '</span>' +
      '<span class="action-target">' + action.target + '</span>' +
      '<span class="action-flag">' + (action.existed ? "existing" : "new") + '</span>';
    details.appendChild(summary);
    var pre = document.createElement("pre");
    pre.className = "diff";
    pre.innerHTML = renderDiff(action.diff || "");
    details.appendChild(pre);
    li.appendChild(details);
    list.appendChild(li);
  });
}

function renderDiff(text) {
  return text.split("\n").map(function (line) {
    var escaped = line.replace(/&/g, "&amp;").replace(/</g, "&lt;");
    if (line.indexOf("+++") === 0 || line.indexOf("---") === 0) return escaped;
    if (line.indexOf("+") === 0) return '<span class="line-add">' + escaped + "</span>";
    if (line.indexOf("-") === 0) return '<span class="line-del">' + escaped + "</span>";
    return "<span>" + escaped + "</span>";
  }).join("\n");
}

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
  document.getElementById("install-current").textContent = p.current || "Working\u2026";
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
