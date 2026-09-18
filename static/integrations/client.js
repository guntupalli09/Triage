(function () {
  const root = document.getElementById("app");
  if (!root) return;
  const client = root.dataset.client || "api";
  const base = (root.dataset.base || "").replace(/\/$/, "");
  const tokenKey = "tc_integration_token";

  function token() { return localStorage.getItem(tokenKey) || ""; }
  function setToken(t) { localStorage.setItem(tokenKey, t); }

  function authHeaders(extra) {
    const headers = Object.assign({
      "X-TriageCounsel-Client": client,
    }, extra || {});
    if (token()) headers.Authorization = "Bearer " + token();
    return headers;
  }

  async function api(path, opts) {
    opts = opts || {};
    const headers = authHeaders(Object.assign({ "Content-Type": "application/json" }, opts.headers || {}));
    const res = await fetch(base + path, Object.assign({}, opts, { headers }));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) {
      const detail = data.detail || res.statusText;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  async function downloadExport(reviewId, format) {
    const res = await fetch(base + "/api/v1/reviews/" + reviewId + "/export?format=" + encodeURIComponent(format || "docx"), {
      headers: authHeaders(),
    });
    if (!res.ok) {
      const data = await res.json().catch(function () { return {}; });
      const detail = data.detail || res.statusText;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    const blob = await res.blob();
    const disp = res.headers.get("Content-Disposition") || "";
    const match = /filename="?([^"]+)"?/.exec(disp);
    const name = match ? match[1] : (format === "package" ? "NegotiationPackage.zip" : "Redlined.docx");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function h(html) { root.innerHTML = html; }

  async function getDocumentText() {
    if (client === "word" && window.Word) {
      return Word.run(async function (context) {
        const body = context.document.body;
        body.load("text");
        await context.sync();
        return body.text;
      });
    }
    if (client === "google_docs" && window.google && google.script && google.script.run) {
      return new Promise(function (resolve, reject) {
        google.script.run.withSuccessHandler(resolve).withFailureHandler(reject).getDocumentText();
      });
    }
    const existing = document.getElementById("manual-text");
    return existing ? existing.value : "";
  }

  async function highlightExcerpt(excerpt) {
    if (!excerpt) return false;
    if (client === "word" && window.Word) {
      return Word.run(async function (context) {
        const results = context.document.body.search(excerpt.substring(0, 255), { matchCase: false });
        results.load("items");
        await context.sync();
        if (!results.items.length) return false;
        results.items[0].select();
        results.items[0].font.highlightColor = "#FEF3C7";
        await context.sync();
        return true;
      });
    }
    if (client === "google_docs" && window.google && google.script && google.script.run) {
      return new Promise(function (resolve, reject) {
        google.script.run.withSuccessHandler(resolve).withFailureHandler(reject).highlightText(excerpt);
      });
    }
    return false;
  }

  async function insertHostComment(excerpt, comment) {
    if (client === "word" && window.Word) {
      return Word.run(async function (context) {
        const results = context.document.body.search((excerpt || "").substring(0, 255), { matchCase: false });
        results.load("items");
        await context.sync();
        if (!results.items.length) return false;
        if (results.items[0].insertComment) {
          results.items[0].insertComment(comment);
          await context.sync();
          return true;
        }
        return false;
      });
    }
    if (client === "google_docs" && window.google && google.script && google.script.run) {
      return new Promise(function (resolve, reject) {
        google.script.run.withSuccessHandler(resolve).withFailureHandler(reject).insertComment(excerpt, comment);
      });
    }
    return false;
  }

  async function applyRedline(excerpt, replacement) {
    if (!excerpt || !replacement) return false;
    if (client === "word" && window.Word) {
      return Word.run(async function (context) {
        const results = context.document.body.search(excerpt.substring(0, 255), { matchCase: true });
        results.load("items");
        await context.sync();
        if (results.items.length !== 1) return false;
        results.items[0].insertText(replacement, "Replace");
        await context.sync();
        return true;
      });
    }
    if (client === "google_docs" && window.google && google.script && google.script.run) {
      return new Promise(function (resolve, reject) {
        google.script.run.withSuccessHandler(resolve).withFailureHandler(reject).suggestReplacement(excerpt, replacement);
      });
    }
    return false;
  }

  function renderLogin(err) {
    h(`<h1>TriageCounsel</h1>
      <p class="muted">Sign in. The add-in does not evaluate legal policy locally.</p>
      ${err ? `<div class="err">${err}</div>` : ""}
      <label>Email</label><input id="email" type="email">
      <label>Password</label><input id="password" type="password">
      <div class="row"><button class="primary" id="login">Sign in</button></div>`);
    document.getElementById("login").onclick = async function () {
      try {
        const data = await api("/api/v1/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: document.getElementById("email").value,
            password: document.getElementById("password").value,
            client_kind: client,
          }),
        });
        setToken(data.token);
        await renderApp();
      } catch (e) { renderLogin(e.message); }
    };
  }

  async function renderApp() {
    let me;
    try { me = await api("/api/v1/me"); }
    catch (e) { renderLogin(e.message); return; }
    let playbooks = { playbooks: [] };
    try { playbooks = await api("/api/v1/playbooks"); } catch (e) { /* requester */ }
    const workspaces = me.workspaces || [];
    const workspaceOptions = workspaces.map(function (w) {
      const selected = w.id === me.workspace_id ? " selected" : "";
      return `<option value="${w.id}"${selected}>${w.name}</option>`;
    }).join("");
    h(`<h1>TriageCounsel</h1>
      <p class="muted">${me.email} · tenant ${me.tenant_id} · ${client.replace("_", " ")}</p>
      <label>Workspace</label>
      <select id="workspace">${workspaceOptions}</select>
      <label>Playbook</label>
      <select id="playbook">${(playbooks.playbooks || []).map(p => `<option value="${p.id}">${p.name}</option>`).join("")}</select>
      ${(!window.Word && !(window.google && google.script)) ? `<label>Document text (host not detected)</label><textarea id="manual-text" rows="8" placeholder="Paste the contract if the host add-in is not loaded."></textarea>` : ""}
      <div class="row">
        <button class="primary" id="run">Review current document</button>
        <button class="secondary" id="reconfirm">Reconfirm after edits</button>
        <button class="secondary" id="export">Export redlined DOCX</button>
        <button class="secondary" id="logout">Sign out</button>
      </div>
      <div id="status" class="muted"></div>
      <div id="findings"></div>`);
    document.getElementById("logout").onclick = function () { localStorage.removeItem(tokenKey); renderLogin(); };
    document.getElementById("export").onclick = async function () {
      const id = localStorage.getItem("tc_review_id");
      const status = document.getElementById("status");
      if (!id) { status.textContent = "Run a review first."; return; }
      status.textContent = "Building redlined document from persisted findings…";
      try {
        await downloadExport(id, "docx");
        status.textContent = "Downloaded redlined DOCX from TriageCounsel. Prior review state is unchanged.";
      } catch (e) { status.textContent = e.message; }
    };
    document.getElementById("run").onclick = async function () {
      const status = document.getElementById("status");
      status.textContent = "Extracting and reviewing…";
      try {
        const text = await getDocumentText();
        if (!text || !text.trim()) throw new Error("No document text found.");
        const workspaceEl = document.getElementById("workspace");
        const review = await api("/api/v1/reviews", {
          method: "POST",
          body: JSON.stringify({
            document_text: text,
            filename: client === "word" ? "word-document.docx" : "google-doc.gdoc",
            playbook_id: document.getElementById("playbook").value ? Number(document.getElementById("playbook").value) : null,
            workspace_id: workspaceEl && workspaceEl.value ? Number(workspaceEl.value) : null,
            source: client,
          }),
        });
        localStorage.setItem("tc_review_id", String(review.id));
        renderFindings(review);
        status.textContent = "Review " + review.id + " · " + (review.findings || []).length + " findings. Policy authority: TriageCounsel server.";
      } catch (e) { status.textContent = e.message; }
    };
    document.getElementById("reconfirm").onclick = async function () {
      const id = localStorage.getItem("tc_review_id");
      const status = document.getElementById("status");
      if (!id) { status.textContent = "Run a review first."; return; }
      try {
        const text = await getDocumentText();
        const data = await api("/api/v1/reviews/" + id + "/reconfirm", {
          method: "POST",
          body: JSON.stringify({ document_text: text, reevaluate_affected: false }),
        });
        renderFindings(data.review);
        const affected = (data.change_aware.affected_clause_types || []).join(", ") || "none";
        status.textContent = "Reconfirmed. Affected: " + affected;
      } catch (e) { status.textContent = e.message; }
    };
  }

  function renderFindings(review) {
    const box = document.getElementById("findings");
    if (!box) return;
    box.innerHTML = (review.findings || []).map(function (f) {
      return `<div class="finding sev-${f.severity || "low"}" data-key="${f.finding_key}">
        <div><strong>${f.policy_area || f.title}</strong> · ${f.outcome || f.severity || ""}</div>
        <div class="muted">${f.why_this_decision || f.explanation || ""}</div>
        <div class="muted">Evidence: ${(f.evidence || "").slice(0, 240)}</div>
        ${f.stale ? `<div class="err">${f.stale_reason || "Needs reconfirmation"}</div>` : ""}
        <div class="row">
          <button class="secondary" data-act="goto">Show in document</button>
          <button class="secondary" data-act="comment">Insert comment</button>
          ${f.suggested_redline ? `<button class="primary" data-act="redline">Apply redline</button>` : ""}
        </div>
      </div>`;
    }).join("");
    box.querySelectorAll(".finding").forEach(function (el) {
      const finding = (review.findings || []).find(x => x.finding_key === el.dataset.key);
      el.querySelector('[data-act="goto"]').onclick = function () { highlightExcerpt(finding.evidence); };
      el.querySelector('[data-act="comment"]').onclick = async function () {
        const comment = finding.suggested_comment || finding.why_this_decision || finding.title;
        const inserted = await insertHostComment(finding.evidence, comment);
        await api("/api/v1/reviews/" + review.id + "/comments", {
          method: "POST",
          body: JSON.stringify({ finding_key: finding.finding_key, comment: comment, inserted_in_host: !!inserted }),
        });
      };
      const redlineBtn = el.querySelector('[data-act="redline"]');
      if (redlineBtn) {
        redlineBtn.onclick = async function () {
          const ok = await applyRedline(finding.evidence, finding.suggested_redline);
          if (!ok) {
            alert("Redline was not applied automatically because the evidence excerpt is not a unique match. Insert a comment instead.");
            return;
          }
          await api("/api/v1/reviews/" + review.id + "/actions", {
            method: "POST",
            body: JSON.stringify({ finding_key: finding.finding_key, action: "accepted" }),
          });
        };
      }
    });
  }

  function boot() {
    if (window.Office && Office.onReady) {
      Office.onReady(function () { token() ? renderApp() : renderLogin(); });
    } else {
      token() ? renderApp() : renderLogin();
    }
  }
  boot();
})();
