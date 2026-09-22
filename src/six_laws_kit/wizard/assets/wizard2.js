"use strict";

/* Every DOM builder for the wizard: the Scan step's tree cards, the Register-heads table, and
   the Review step's grouped action list. All three walk the same forest in the same order and
   use the same indentation step, so one tree reads as one unit wherever it appears.

   The page loads this file straight after wizard.js. Nothing here runs at load time: wizard.js
   calls into it only from event and poll callbacks, by which point both scripts are in scope. */

var INDENT_STEP_PX = 20;
var treeIdSeq = 0;

function cssEscape(s) { return s.replace(/["\\]/g, "\\$&"); }

function span(className, text) {
  var el = document.createElement("span");
  el.className = className;
  el.textContent = text;
  return el;
}

function tag(text) { return span("tree-tag", text); }

function plural(count, one, many) { return count + " " + (count === 1 ? one : many); }

function sessionText(tree) {
  return tree.has_session ? "last session " + tree.last_session : "no prior session";
}

function countSubtrees(tree) {
  return (tree.subtrees || []).reduce(function (total, sub) {
    return total + 1 + countSubtrees(sub);
  }, 0);
}

/* Flattens one tree into `{path, name, depth}` rows: the head first, then every subtree under
   it, depth first, to any depth. The Heads table and the Review list both order by this. */
function flattenTree(tree, depth) {
  var rows = [{ path: tree.path, name: tree.name, depth: depth }];
  (tree.subtrees || []).forEach(function (sub) {
    rows = rows.concat(flattenTree(sub, depth + 1));
  });
  return rows;
}

/* Scan: one card per tree ------------------------------------------------ */
function renderForest(trees) {
  var root = document.getElementById("tree-root");
  root.innerHTML = "";
  trees.forEach(function (tree) { root.appendChild(treeCard(tree)); });
  var subtrees = trees.reduce(function (total, t) { return total + countSubtrees(t); }, 0);
  document.getElementById("forest-lead").textContent =
    plural(trees.length, "tree", "trees") + " in your forest, holding " +
    plural(subtrees, "subtree", "subtrees") + " between them.";
}

function treeCard(tree) {
  var card = document.createElement("fieldset");
  card.className = "tree-card tree-selected";
  var legend = document.createElement("legend");
  legend.textContent = tree.name;
  card.appendChild(legend);
  var box = document.createElement("input");
  box.type = "checkbox";
  box.id = "tree-cb-" + treeIdSeq++;
  box.checked = true;
  box.dataset.path = tree.path;
  box.addEventListener("change", function () {
    card.classList.toggle("tree-selected", box.checked);
  });
  card.appendChild(treeHeadRow(tree, box));
  if (tree.subtrees && tree.subtrees.length) {
    card.appendChild(subtreeList(tree.subtrees, 1, tree.name));
  }
  return card;
}

function treeHeadRow(tree, box) {
  var row = document.createElement("div");
  row.className = "tree-head";
  var label = document.createElement("label");
  label.className = "tree-name";
  label.htmlFor = box.id;
  label.textContent = tree.name;
  var count = countSubtrees(tree);
  row.appendChild(box);
  row.appendChild(label);
  row.appendChild(span("tree-path", tree.path));
  row.appendChild(span("tree-date", sessionText(tree)));
  row.appendChild(tag(count ? plural(count, "subtree", "subtrees") : "no subtrees"));
  return row;
}

/* The subtree hierarchy under one head: nested <ul>s, `aria-level` per item, connector lines
   drawn in CSS. Grandchildren and deeper are included; there is no depth limit. */
function subtreeList(subtrees, level, headName) {
  var ul = document.createElement("ul");
  ul.className = "subtrees";
  if (level === 1) ul.setAttribute("aria-label", "Subtrees of " + headName);
  subtrees.forEach(function (sub) {
    var li = document.createElement("li");
    li.setAttribute("aria-level", String(level));
    var row = document.createElement("div");
    row.className = "subtree-row";
    row.appendChild(span("tree-name", sub.name));
    row.appendChild(span("tree-path", sub.path));
    row.appendChild(span("tree-date", sessionText(sub)));
    row.appendChild(tag("inherited"));
    li.appendChild(row);
    if (sub.subtrees && sub.subtrees.length) {
      li.appendChild(subtreeList(sub.subtrees, level + 1, headName));
    }
    ul.appendChild(li);
  });
  return ul;
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

/* Register heads: the same trees, in the same order, as grouped table rows --------- */
function renderHeadsRows(trees) {
  var body = document.getElementById("heads-tbody");
  body.innerHTML = "";
  trees.forEach(function (tree) {
    body.appendChild(groupRow("Tree: " + tree.name));
    flattenTree(tree, 0).forEach(function (r) { body.appendChild(headsRow(r)); });
  });
}

function groupRow(text) {
  var tr = document.createElement("tr");
  tr.className = "heads-group";
  var th = document.createElement("th");
  th.colSpan = 3;
  th.scope = "rowgroup";
  th.textContent = text;
  tr.appendChild(th);
  return tr;
}

function headsRow(r) {
  headsStart[r.path] = Date.now();
  var tr = document.createElement("tr");
  tr.dataset.path = r.path;
  var name = document.createElement("td");
  name.style.paddingLeft = (12 + r.depth * INDENT_STEP_PX) + "px";
  name.appendChild(span("tree-name", r.name));
  name.appendChild(tag(r.depth ? "subtree" : "head"));
  var status = document.createElement("td");
  var badge = span("badge badge-waiting", "waiting");
  badge.dataset.role = "badge";
  status.appendChild(badge);
  var elapsed = document.createElement("td");
  elapsed.dataset.role = "elapsed";
  elapsed.textContent = "0.0s";
  tr.appendChild(name);
  tr.appendChild(status);
  tr.appendChild(elapsed);
  return tr;
}

/* Review: the plan, grouped by tree in the Scan step's order ---------------------- */
function renderReview(data) {
  renderWarnings(data.warnings || []);
  var host = document.getElementById("review-actions");
  host.innerHTML = "";
  groupActions(data.actions || [], state.selectedTrees).forEach(function (group) {
    if (group.items.length) host.appendChild(reviewGroup(group));
  });
}

function renderWarnings(warnings) {
  var list = document.getElementById("review-warnings");
  list.innerHTML = "";
  warnings.forEach(function (w) {
    var li = document.createElement("li");
    li.textContent = w;
    list.appendChild(li);
  });
  list.hidden = warnings.length === 0;
}

/* An action belongs to the tree whose directory holds its target file; everything else is a
   shared file that belongs to the forest as a whole and is listed first. */
function groupActions(actions, trees) {
  var shared = { title: "Shared files (the whole forest)", items: [] };
  var owners = {};
  var groups = (trees || []).map(function (tree) {
    var group = { title: "Tree: " + tree.name, items: [] };
    flattenTree(tree, 0).forEach(function (r) { owners[r.path] = { group: group, depth: r.depth }; });
    return group;
  });
  actions.forEach(function (action) {
    var owner = owners[parentDir(action.target)];
    if (owner) owner.group.items.push({ action: action, depth: owner.depth });
    else shared.items.push({ action: action, depth: 0 });
  });
  return [shared].concat(groups);
}

function parentDir(target) { return String(target).replace(/[\\/][^\\/]*$/, ""); }

function reviewGroup(group) {
  var section = document.createElement("section");
  section.className = "review-group";
  var heading = document.createElement("h3");
  heading.textContent = group.title;
  section.appendChild(heading);
  var list = document.createElement("ul");
  list.className = "actions";
  group.items.forEach(function (item) {
    var li = actionItem(item.action);
    li.style.marginLeft = item.depth * INDENT_STEP_PX + "px";
    list.appendChild(li);
  });
  section.appendChild(list);
  return section;
}

function actionItem(action) {
  var li = document.createElement("li");
  var details = document.createElement("details");
  var summary = document.createElement("summary");
  summary.appendChild(span("action-kind", action.kind));
  summary.appendChild(span("action-target", action.target));
  summary.appendChild(span("action-flag", action.existed ? "existing" : "new"));
  details.appendChild(summary);
  var pre = document.createElement("pre");
  pre.className = "diff";
  pre.innerHTML = renderDiff(action.diff || "");
  details.appendChild(pre);
  li.appendChild(details);
  return li;
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
