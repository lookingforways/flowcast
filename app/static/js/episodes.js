// Episodes page logic

let currentEpisodeId = null;

// Filter by status
document.getElementById('statusFilter').addEventListener('change', function () {
  const val = this.value;
  document.querySelectorAll('#episodesTable tbody tr').forEach(row => {
    row.style.display = (!val || row.dataset.status === val) ? '' : 'none';
  });
});

// Download / Publish buttons (direct actions)
document.querySelectorAll('.btn-action[data-action="download"], .btn-action[data-action="publish"]').forEach(btn => {
  btn.addEventListener('click', async () => {
    const action = btn.dataset.action;
    const id = btn.dataset.id;
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    try {
      await apiRequest(`/api/episodes/${id}/${action}`, 'POST');
      showToast(`${action === 'download' ? 'Descarga' : 'Publicación'} iniciada`);
      setTimeout(() => location.reload(), 2000);
    } catch (e) {
      showToast('Error: ' + e.message, 'danger');
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  });
});

// Render button — opens modal
document.querySelectorAll('.btn-action[data-action="render"]').forEach(btn => {
  btn.addEventListener('click', () => {
    currentEpisodeId = btn.dataset.id;
    document.getElementById('renderEpisodeTitle').textContent = btn.dataset.episodeTitle || '';
  });
});

// Confirm render in modal
document.getElementById('confirmRenderBtn').addEventListener('click', async () => {
  if (!currentEpisodeId) return;
  const templateId = document.getElementById('renderTemplateSelect').value;
  const btn = document.getElementById('confirmRenderBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Iniciando...';
  try {
    let url = `/api/episodes/${currentEpisodeId}/render`;
    if (templateId) url += `?template_id=${templateId}`;
    await apiRequest(url, 'POST');
    bootstrap.Modal.getInstance(document.getElementById('renderModal')).hide();
    showToast('Render iniciado. Puede tardar varios minutos.');
    setTimeout(() => location.reload(), 2500);
  } catch (e) {
    showToast('Error: ' + e.message, 'danger');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-film me-1"></i>Renderizar';
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
