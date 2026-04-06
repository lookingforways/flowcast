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
  const text = document.createElement('span');
  text.textContent = msg;
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn-close';
  btn.addEventListener('click', () => el.remove());
  el.appendChild(text);
  el.appendChild(btn);
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// Set background color on waveform color swatches from data-color attribute
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.wave-color-swatch[data-color]').forEach(el => {
    el.style.backgroundColor = el.dataset.color;
  });
});

// ── Theme toggle ─────────────────────────────────────────────────────────────
(function () {
  const toggle = document.getElementById('theme-toggle');
  const icon   = document.getElementById('theme-icon');
  const label  = document.getElementById('theme-label');

  function applyThemeUI(theme) {
    if (!icon || !label) return;
    if (theme === 'dark') {
      icon.className  = 'bi bi-sun';
      label.textContent = 'Claro';
    } else {
      icon.className  = 'bi bi-moon';
      label.textContent = 'Oscuro';
    }
  }

  // Sync button label with current theme on load
  applyThemeUI(document.documentElement.getAttribute('data-theme') || 'light');

  if (toggle) {
    toggle.addEventListener('click', function () {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next    = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('fc-theme', next);
      applyThemeUI(next);
    });
  }
}());
