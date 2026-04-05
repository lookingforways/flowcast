// Episodes page logic

let currentEpisodeId = null;
const renderModal = document.getElementById('renderModal');

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

// Download / Publish buttons (direct actions)
document.querySelectorAll('.btn-action[data-action="download"], .btn-action[data-action="publish"]').forEach(btn => {
  btn.addEventListener('click', async () => {
    const action = btn.dataset.action;
    const id = btn.dataset.id;
    const restore = btnLoading(btn);
    try {
      await apiRequest(`/api/episodes/${id}/${action}`, 'POST');
      showToast(action === 'download' ? 'Descarga iniciada' : 'Publicación iniciada');
      setTimeout(() => location.reload(), 2000);
    } catch (e) {
      showToast('Error: ' + e.message, 'danger');
      restore();
    }
  });
});

// Render button — opens dialog
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
    showToast('Render iniciado. Puede tardar varios minutos.');
    setTimeout(() => location.reload(), 2500);
  } catch (e) {
    showToast('Error: ' + e.message, 'danger');
    restore();
  }
});

// Auto-refresh running jobs every 10s
function refreshRunningRows() {
  const hasRunning = document.querySelectorAll('[data-status="downloaded"]').length > 0;
  if (hasRunning) {
    setTimeout(() => location.reload(), 10000);
  }
}
refreshRunningRows();
