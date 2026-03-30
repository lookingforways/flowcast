// Flowcast — shared utilities

// Initialize Bootstrap tooltips
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });
});

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
  el.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  el.style.cssText = 'bottom:1.5rem;right:1.5rem;z-index:9999;min-width:250px';
  el.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
