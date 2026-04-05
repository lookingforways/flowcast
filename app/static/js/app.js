// Flowcast — shared utilities

// Generic API request helper
async function apiRequest(url, method = 'GET', body = null) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(url, opts);
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try { const data = await resp.json(); msg = data.detail || JSON.stringify(data); } catch {}
    throw new Error(msg);
  }
  return resp.status === 204 ? null : resp.json();
}

// Show a temporary toast-like banner
function showToast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `alert alert-${type} fc-toast`;
  el.innerHTML = `<span>${msg}</span><button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// Set background color on waveform color swatches from data-color attribute
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.wave-color-swatch[data-color]').forEach(el => {
    el.style.backgroundColor = el.dataset.color;
  });
});
