// Episodes page logic

let currentEpisodeId = null;
const renderModal = document.getElementById('renderModal');

// Close dialogs via data-close-dialog
document.querySelectorAll('[data-close-dialog]').forEach(function (btn) {
  btn.addEventListener('click', function () { btn.closest('dialog').close(); });
});

// Podcast filter — navigate on change
document.getElementById('podcastFilter').addEventListener('change', function () {
  location.href = '/episodes' + (this.value ? '?podcast_id=' + this.value : '');
});

// Helper: set a button to loading state, returns a restore function
function btnLoading(btn, text) {
  const snapshot = btn.cloneNode(true);
  btn.disabled = true;
  btn.textContent = '';
  const spinner = document.createElement('span');
  spinner.className = 'spinner-border spinner-border-sm';
  btn.appendChild(spinner);
  if (text) {
    btn.appendChild(document.createTextNode('\u00a0' + text));
  }
  return () => {
    btn.disabled = false;
    btn.textContent = '';
    snapshot.childNodes.forEach(n => btn.appendChild(n.cloneNode(true)));
  };
}

// Filter by status
document.getElementById('statusFilter').addEventListener('change', function () {
  const val = this.value;
  document.querySelectorAll('#episodesTable tbody tr').forEach(row => {
    row.classList.toggle('d-none', !!(val && row.dataset.status !== val));
  });
});

// ── Progress bar helpers ─────────────────────────────────────────────────────

const _phaseLabel = {
  download: 'Descargando MP3…',
  render:   'Renderizando…',
  upload:   'Subiendo a YouTube…',
};

function showRowProgress(episodeId) {
  const row = document.querySelector(`tr[data-id="${episodeId}"]`);
  if (!row) return;
  row.querySelector('.ep-actions').classList.add('d-none');
  row.querySelector('.ep-progress').classList.remove('d-none');
}

function updateRowProgress(episodeId, pct, phase) {
  const prog = document.querySelector(`.ep-progress[data-id="${episodeId}"]`);
  if (!prog) return;
  prog.querySelector('.fc-progress-bar').style.width = pct + '%';
  prog.querySelector('.fc-progress-label').textContent =
    (_phaseLabel[phase] || 'Procesando…') + ' ' + pct + '%';
}

function pollProgress(episodeId, intervalMs) {
  intervalMs = intervalMs || 1500;
  const timer = setInterval(async () => {
    try {
      const data = await apiRequest(`/api/episodes/${episodeId}/progress`);
      if (data.phase) {
        updateRowProgress(episodeId, data.pct, data.phase);
      } else {
        // Operation finished — reload to reflect new status
        clearInterval(timer);
        location.reload();
      }
    } catch (_) {
      clearInterval(timer);
      location.reload();
    }
  }, intervalMs);
  return timer;
}

// ── Download / Publish buttons ───────────────────────────────────────────────

document.querySelectorAll('.btn-action[data-action="download"], .btn-action[data-action="publish"]').forEach(btn => {
  btn.addEventListener('click', async () => {
    const action = btn.dataset.action;
    const id = btn.dataset.id;
    const restore = btnLoading(btn);
    try {
      await apiRequest(`/api/episodes/${id}/${action}`, 'POST');
      showRowProgress(id);
      pollProgress(id);
    } catch (e) {
      showToast('Error: ' + e.message, 'danger');
      restore();
    }
  });
});

// ── Render button — opens dialog ─────────────────────────────────────────────

document.querySelectorAll('.btn-action[data-action="render"]').forEach(btn => {
  btn.addEventListener('click', () => {
    currentEpisodeId = btn.dataset.id;
    document.getElementById('renderEpisodeTitle').textContent = btn.dataset.episodeTitle || '';
    renderModal.showModal();
  });
});

// Confirm render in dialog
document.getElementById('confirmRenderBtn').addEventListener('click', async () => {
  if (!currentEpisodeId) return;
  const templateId = document.getElementById('renderTemplateSelect').value;
  const btn = document.getElementById('confirmRenderBtn');
  const restore = btnLoading(btn, 'Iniciando...');
  try {
    let url = `/api/episodes/${currentEpisodeId}/render`;
    if (templateId) url += `?template_id=${templateId}`;
    await apiRequest(url, 'POST');
    renderModal.close();
    showRowProgress(currentEpisodeId);
    pollProgress(currentEpisodeId);
  } catch (e) {
    showToast('Error: ' + e.message, 'danger');
    restore();
  }
});

// ── Auto-refresh if any row is already processing (page reload mid-operation) ─

document.querySelectorAll('.ep-progress').forEach(prog => {
  const id = prog.dataset.id;
  // Check if this episode already has an active operation
  apiRequest(`/api/episodes/${id}/progress`).then(data => {
    if (data.phase) {
      showRowProgress(id);
      updateRowProgress(id, data.pct, data.phase);
      pollProgress(id);
    }
  }).catch(() => {});
});
