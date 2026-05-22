/* emails.js — inbox, detail, AI processing, compose modal, thread toggle */

/* ------------------------------------------------------------------ */
/* Delete email (email detail page — INBOUND only)                     */
/* ------------------------------------------------------------------ */

async function deleteEmail(emailId) {
  if (!confirm("Delete this email from LogiTrack? This cannot be undone.")) return;
  try {
    const resp = await fetch(`/emails/${emailId}/delete`, { method: "POST" });
    const data = await resp.json();
    if (!data.ok) {
      alert("Delete failed: " + (data.error || "Unknown error"));
      return;
    }
    window.location.href = "/emails";
  } catch (err) {
    alert("Request failed: " + err.message);
  }
}

/* ------------------------------------------------------------------ */
/* AI processing (email detail page)                                    */
/* ------------------------------------------------------------------ */

async function processEmail(emailId) {
  const btn     = document.getElementById("process-btn");
  const spinner = document.getElementById("ai-spinner");
  const panel   = document.getElementById("ai-result-panel");

  if (btn) btn.disabled = true;
  if (spinner) spinner.style.display = "block";
  if (panel) panel.style.opacity = "0.4";

  try {
    const resp = await fetch(`/emails/${emailId}/process`, { method: "POST" });
    const data = await resp.json();

    if (!data.ok) {
      alert("AI processing failed: " + (data.error || "Unknown error"));
      if (btn) btn.disabled = false;
      return;
    }

    if (panel) {
      panel.innerHTML = _buildAiPanel(data);
      panel.style.opacity = "1";
    }
    if (btn) { btn.textContent = "Re-process"; btn.disabled = false; }
  } catch (err) {
    alert("Request failed: " + err.message);
    if (btn) btn.disabled = false;
  } finally {
    if (spinner) spinner.style.display = "none";
    if (panel) panel.style.opacity = "1";
  }
}

function _buildAiPanel(data) {
  const catClass = data.detected_category || "OTHER";
  const catLabel = (data.detected_category || "OTHER").replace(/_/g, " ");
  let refs = "";
  if (data.shipment_reference)
    refs += `<div class="ai-ref-row"><span class="ai-ref-label">Shipment:</span><span class="ai-ref-value">${_esc(data.shipment_reference)}</span></div>`;
  if (data.invoice_reference)
    refs += `<div class="ai-ref-row"><span class="ai-ref-label">Invoice:</span><span class="ai-ref-value">${_esc(data.invoice_reference)}</span></div>`;
  return `
    <p class="ai-result-summary">${_esc(data.summary || "")}</p>
    <span class="ai-category-badge ${_esc(catClass)}">${_esc(catLabel)}</span>
    <div class="ai-refs">${refs}</div>
  `;
}

/* ------------------------------------------------------------------ */
/* AI reply generation (email detail page)                              */
/* ------------------------------------------------------------------ */

async function generateReply(emailId) {
  const btn       = document.getElementById("generate-reply-btn");
  const spinnerRow = document.getElementById("reply-spinner");
  const textarea  = document.getElementById("reply-body");

  if (btn) btn.disabled = true;
  if (spinnerRow) spinnerRow.style.display = "flex";

  try {
    const resp = await fetch(`/emails/${emailId}/auto-reply`, { method: "POST" });
    const data = await resp.json();

    if (!data.ok) {
      alert("Reply generation failed: " + (data.error || "Unknown error"));
      return;
    }
    if (textarea) { textarea.value = data.reply_text; textarea.focus(); }
  } catch (err) {
    alert("Request failed: " + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (spinnerRow) spinnerRow.style.display = "none";
  }
}

/* ------------------------------------------------------------------ */
/* Reply / Reply All / Forward (email detail page)                      */
/* ------------------------------------------------------------------ */

function setReplyMode(mode) {
  if (typeof EMAIL_DATA === "undefined") return;

  const toInput       = document.getElementById("reply-to");
  const ccInput       = document.getElementById("reply-cc");
  const bccInput      = document.getElementById("reply-bcc");
  const subjectInput  = document.getElementById("reply-subject-hidden");
  const threadInput   = document.getElementById("reply-thread-id");
  const bodyArea      = document.getElementById("reply-body");
  const cardHeader    = document.getElementById("reply-card-header");

  if (!toInput) return;

  if (mode === "reply") {
    toInput.value      = _cleanReplyTo(EMAIL_DATA.direction, EMAIL_DATA.from_email, EMAIL_DATA.to_email);
    ccInput.value      = "";
    bccInput.value     = "";
    subjectInput.value = "Re: " + (EMAIL_DATA.subject || "");
    threadInput.value  = EMAIL_DATA.gmail_thread_id || "";
    bodyArea.value     = "";
    if (cardHeader) cardHeader.textContent = "Reply";

  } else if (mode === "reply-all") {
    const own = (OWN_EMAIL || "").toLowerCase();
    const replyTo = _cleanReplyTo(EMAIL_DATA.direction, EMAIL_DATA.from_email, EMAIL_DATA.to_email);
    const all = [
      replyTo,
      EMAIL_DATA.direction === "OUTBOUND" ? EMAIL_DATA.from_email : EMAIL_DATA.to_email,
      ...(EMAIL_DATA.cc ? EMAIL_DATA.cc.split(",") : []),
    ]
      .map(e => (e || "").trim())
      .filter(e => e && e.toLowerCase() !== own && !e.toLowerCase().includes("googleusercontent.com"));
    toInput.value      = [...new Set(all)].join(", ");
    ccInput.value      = "";
    bccInput.value     = "";
    subjectInput.value = "Re: " + (EMAIL_DATA.subject || "");
    threadInput.value  = EMAIL_DATA.gmail_thread_id || "";
    bodyArea.value     = "";
    if (cardHeader) cardHeader.textContent = "Reply All";

  } else if (mode === "forward") {
    toInput.value      = "";
    ccInput.value      = "";
    bccInput.value     = "";
    subjectInput.value = "Fwd: " + (EMAIL_DATA.subject || "");
    threadInput.value  = "";
    bodyArea.value     = "\n\n---------- Forwarded message ----------\n"
      + "From: " + (EMAIL_DATA.from_email || "") + "\n"
      + "Subject: " + (EMAIL_DATA.subject || "") + "\n\n"
      + (EMAIL_DATA.body_plain || "");
    if (cardHeader) cardHeader.textContent = "Forward";
    toInput.focus();
  }

  const replyCard = document.querySelector(".reply-card");
  if (replyCard) replyCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ------------------------------------------------------------------ */
/* Bulk delete (inbox page)                                             */
/* ------------------------------------------------------------------ */

function toggleSelectAll(masterCb) {
  document.querySelectorAll(".email-checkbox").forEach(cb => {
    cb.checked = masterCb.checked;
  });
  updateBulkBar();
}

function updateBulkBar() {
  const all      = document.querySelectorAll(".email-checkbox");
  const selected = document.querySelectorAll(".email-checkbox:checked");
  const bar      = document.getElementById("bulk-actions-bar");
  const countEl  = document.getElementById("bulk-count");
  const master   = document.getElementById("select-all-emails");

  if (bar)     bar.hidden = selected.length === 0;
  if (countEl) countEl.textContent = selected.length + " selected";

  if (master) {
    master.indeterminate = selected.length > 0 && selected.length < all.length;
    master.checked       = all.length > 0 && selected.length === all.length;
  }
}

async function bulkDeleteEmails() {
  const checkboxes = document.querySelectorAll(".email-checkbox:checked");
  if (checkboxes.length === 0) return;
  const n = checkboxes.length;
  if (!confirm(`Delete ${n} email${n > 1 ? "s" : ""} from LogiTrack? This cannot be undone.`)) return;

  const ids = Array.from(checkboxes).map(cb => cb.dataset.emailId);
  let failed = 0;
  for (const id of ids) {
    try {
      const resp = await fetch(`/emails/${id}/delete`, { method: "POST" });
      const data = await resp.json();
      if (!data.ok) failed++;
    } catch { failed++; }
  }

  if (failed > 0) alert(`${failed} email(s) could not be deleted.`);
  window.location.reload();
}

/* ------------------------------------------------------------------ */
/* Thread expand / collapse (inbox page)                                */
/* ------------------------------------------------------------------ */

function toggleThread(event, threadId) {
  event.preventDefault();
  event.stopPropagation();
  const extras = document.getElementById(threadId + "-extras");
  const btn    = event.currentTarget;
  if (!extras) return;
  extras.hidden = !extras.hidden;
  btn.classList.toggle("thread-toggle-btn--open", !extras.hidden);
}

/* ------------------------------------------------------------------ */
/* Compose modal (inbox page)                                           */
/* ------------------------------------------------------------------ */

function openComposeModal() {
  const modal = document.getElementById("compose-modal");
  if (!modal) return;
  modal.hidden = false;
  document.body.classList.add("modal-open");
  const first = modal.querySelector("input:not([disabled])");
  if (first) first.focus();
}

function closeComposeModal() {
  const modal = document.getElementById("compose-modal");
  if (!modal) return;
  modal.hidden = true;
  document.body.classList.remove("modal-open");
}

/* ------------------------------------------------------------------ */
/* Init                                                                 */
/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss flash banners
  document.querySelectorAll(".flash-banner").forEach(el => {
    setTimeout(() => {
      el.style.transition = "opacity 0.4s";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });

  // Close compose modal on overlay click
  const modal = document.getElementById("compose-modal");
  if (modal) {
    modal.addEventListener("click", e => {
      if (e.target === modal) closeComposeModal();
    });
  }

  // Close compose modal on Escape
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeComposeModal();
  });
});

/* ------------------------------------------------------------------ */
/* Utility                                                              */
/* ------------------------------------------------------------------ */

function _cleanReplyTo(direction, fromEmail, toEmail) {
  // For outbound emails (we sent them), reply goes to the original recipient
  const raw = direction === "OUTBOUND" ? toEmail : fromEmail;
  if (!raw) return "";
  // Strip autogenerated Google proxy addresses
  if (raw.toLowerCase().includes("googleusercontent.com")) return "";
  if (raw.toLowerCase().startsWith("noreply@")) return "";
  return raw;
}

function _esc(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
