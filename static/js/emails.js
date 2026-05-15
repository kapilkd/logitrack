/* emails.js — email inbox, detail, AI processing */

async function processEmail(emailId) {
  const btn = document.getElementById("process-btn");
  const spinner = document.getElementById("ai-spinner");
  const panel = document.getElementById("ai-result-panel");

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
    if (btn) {
      btn.textContent = "Re-process";
      btn.disabled = false;
    }
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
  if (data.shipment_reference) {
    refs += `<div class="ai-ref-row"><span class="ai-ref-label">Shipment:</span><span class="ai-ref-value">${_esc(data.shipment_reference)}</span></div>`;
  }
  if (data.invoice_reference) {
    refs += `<div class="ai-ref-row"><span class="ai-ref-label">Invoice:</span><span class="ai-ref-value">${_esc(data.invoice_reference)}</span></div>`;
  }

  return `
    <p class="ai-result-summary">${_esc(data.summary || "")}</p>
    <span class="ai-category-badge ${_esc(catClass)}">${_esc(catLabel)}</span>
    <div class="ai-refs">${refs}</div>
  `;
}

async function generateReply(emailId) {
  const btn = document.getElementById("generate-reply-btn");
  const spinnerRow = document.getElementById("reply-spinner");
  const textarea = document.getElementById("reply-body");

  if (btn) btn.disabled = true;
  if (spinnerRow) spinnerRow.style.display = "flex";

  try {
    const resp = await fetch(`/emails/${emailId}/auto-reply`, { method: "POST" });
    const data = await resp.json();

    if (!data.ok) {
      alert("Reply generation failed: " + (data.error || "Unknown error"));
      return;
    }

    if (textarea) {
      textarea.value = data.reply_text;
      textarea.focus();
    }
  } catch (err) {
    alert("Request failed: " + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (spinnerRow) spinnerRow.style.display = "none";
  }
}

function _esc(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Auto-dismiss flash banners after 5 seconds
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash-banner").forEach(el => {
    setTimeout(() => {
      el.style.transition = "opacity 0.4s";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
});
