/* ══════════════════════════════════════════════════
   StockCont Dashboard — SPA Logic
   ══════════════════════════════════════════════════ */

const API = '';  // Same origin
let autoRefreshId = null;
const REFRESH_INTERVAL = 15000; // 15 seconds

// ── State ──────────────────────────────────────────
let currentTab = 'gallery';
let currentImageFilter = 'all';
let currentQueueFilter = 'all';
let currentTasks = {};
let previousTasks = {};
let currentKpis = null;
let currentPhases = [];
let taskPollTimer = null;

// ── Init ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  refreshAll();
  autoRefreshId = setInterval(refreshAll, REFRESH_INTERVAL);
});

// ── Master Refresh ─────────────────────────────────
async function refreshAll() {
  try {
    await Promise.all([
      loadStatus(),
      loadCurrentTab(),
    ]);
    document.getElementById('status-pill').className = 'pill pill-ok';
    document.getElementById('status-pill').textContent = '🟢 Online';
    document.getElementById('last-refresh').textContent = new Date().toLocaleTimeString('pt-BR');
  } catch (err) {
    console.error('Refresh error:', err);
    document.getElementById('status-pill').className = 'pill pill-error';
    document.getElementById('status-pill').textContent = '🔴 Offline';
  }
}

// ── Load Status (KPIs + Pipeline + Tasks) ──────────
async function loadStatus() {
  const [statusRes, tasksRes] = await Promise.all([
    fetch(API + '/api/status'),
    fetch(API + '/api/tasks').catch(() => null),
  ]);
  const data = await statusRes.json();
  let tasks = {};
  if (tasksRes && tasksRes.ok) {
    tasks = await tasksRes.json();
  }

  currentKpis = data.kpis;
  currentPhases = data.phases;

  handleTaskStateChanges(tasks);
  renderKPIs(data.kpis);
  renderPipeline(data.phases, currentTasks);

  // Gemini pill
  const gPill = document.getElementById('gemini-pill');
  if (data.kpis.gemini_configured) {
    gPill.className = 'pill pill-ok';
    gPill.textContent = '🔑 Gemini ✓';
  } else {
    gPill.className = 'pill pill-error';
    gPill.textContent = '🔑 Gemini ✗';
  }
}

function updateTaskPolling() {
  const hasRunning = Object.values(currentTasks).some(function(t) {
    const status = (typeof t === 'object' && t !== null) ? t.status : t;
    return status === 'running';
  });

  if (hasRunning && !taskPollTimer) {
    taskPollTimer = setInterval(pollTasksOnly, 1500);
  } else if (!hasRunning && taskPollTimer) {
    clearInterval(taskPollTimer);
    taskPollTimer = null;
  }
}

async function pollTasksOnly() {
  try {
    const res = await fetch(API + '/api/tasks');
    if (!res.ok) return;
    const tasks = await res.json();
    handleTaskStateChanges(tasks);
    if (currentPhases.length > 0) {
      renderPipeline(currentPhases, currentTasks);
    }
    if (currentTab === 'agencies') {
      loadAgencies();
    } else if (currentTab === 'matrix') {
      loadMatrix();
    } else if (currentTab === 'backup') {
      loadBackup();
    } else if (currentTab === 'seasonal') {
      loadSeasonal();
    } else if (currentTab === 'daemon') {
      loadDaemon();
    }
  } catch (e) {
    console.error('Error polling tasks:', e);
  }
}

function handleTaskStateChanges(newTasks) {
  // Preserve any optimistic running task if it was started in the last 4 seconds and hasn't appeared yet
  const now = Date.now();
  for (const [key, oldTask] of Object.entries(currentTasks)) {
    if (oldTask && oldTask.status === 'running' && !(key in newTasks)) {
      const started = oldTask.started_at ? new Date(oldTask.started_at).getTime() : now;
      if (now - started < 4000) {
        newTasks[key] = oldTask;
      }
    }
  }

  for (const [taskKey, task] of Object.entries(newTasks)) {
    const prev = previousTasks[taskKey];
    const prevStatus = prev ? ((typeof prev === 'object' && prev !== null) ? prev.status : prev) : null;
    const currStatus = (typeof task === 'object' && task !== null) ? task.status : task;

    if (prevStatus === 'running' && currStatus !== 'running') {
      const phaseMatch = taskKey.match(/phase-(\d+)/);
      const phaseNum = phaseMatch ? phaseMatch[1] : null;
      const taskLabel = phaseNum ? ('Fase ' + phaseNum) : (taskKey === 'backup' ? 'Backup' : taskKey);

      const logsStr = (typeof task === 'object' && task.logs) ? task.logs.join(' ') : '';
      const lastLog = (typeof task === 'object' && task.last_log) ? task.last_log : '';

      if (currStatus === 'completed') {
        if (phaseNum === '2') {
          if (logsStr.includes('GEMINI_API_KEY')) {
            showToast('⚠️ Fase 2: GEMINI_API_KEY não configurada no arquivo .env!');
          } else if (logsStr.includes('No trends to process') || logsStr.includes('Nenhuma tendência')) {
            showToast('ℹ️ Fase 2: Nenhuma tendência encontrada. Execute a Fase 1 (Olheiro) primeiro!');
          } else if (logsStr.includes('0 new items') || logsStr.includes('0 items') || lastLog.includes('0 items')) {
            showToast('ℹ️ Fase 2: Todos os prompts já estavam gerados. Fila 100% atualizada!');
          } else {
            showToast('✅ Fase 2 (Diretor de Arte) concluída com sucesso!');
          }
        } else if (phaseNum === '3') {
          if (logsStr.includes('Todos os prompts pendentes foram processados') || logsStr.includes('0 pendentes')) {
            showToast('ℹ️ Fase 3: Todos os prompts já foram gerados. Fila 100% concluída!');
          } else {
            showToast('✅ ' + taskLabel + ' concluída com sucesso!');
          }
        } else {
          showToast('✅ ' + taskLabel + ' concluída com sucesso!');
        }
      } else if (currStatus === 'failed') {
        const rc = (typeof task === 'object' && task.returncode !== null && task.returncode !== undefined) ? task.returncode : '';
        if (lastLog === 'Process terminated by user') {
          showToast('🛑 ' + taskLabel + ' interrompida pelo usuário.');
        } else {
          showToast('❌ ' + taskLabel + ' falhou' + (rc !== '' ? (' (rc=' + rc + ')') : '') + '. ' + (lastLog ? ('Detalhe: ' + lastLog) : ''));
        }
      }

      setTimeout(refreshAll, 600);
    }
  }

  previousTasks = Object.assign({}, newTasks);
  currentTasks = newTasks;
  updateTaskPolling();
}

function renderKPIs(k) {
  setText('kpi-val-trends', k.trends);
  setText('kpi-val-prompts', k.prompts_total);
  setText('kpi-val-queue', k.queue_generated + '/' + k.queue_total);
  setText('kpi-val-images', k.final_images);
  setText('kpi-val-cataloged', k.cataloged);
  setText('kpi-val-distributed', k.distributed);

  const pFill = document.getElementById('queue-progress');
  if (pFill) pFill.style.width = k.queue_percent + '%';
}

async function stopTask(taskKey) {
  const phaseMatch = taskKey.match(/phase-(\d+)/);
  const label = phaseMatch ? ('Fase ' + phaseMatch[1]) : taskKey;
  if (!confirm('Deseja interromper a execução de ' + label + '?')) return;
  showToast('🛑 Interrompendo ' + label + '…');
  try {
    const res = await fetch(API + '/api/tasks/' + encodeURIComponent(taskKey) + '/stop', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('🛑 ' + label + ' interrompida.');
      pollTasksOnly();
    } else {
      showToast('⚠️ O processo já havia finalizado.');
      pollTasksOnly();
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

function renderPipeline(phases, tasks) {
  tasks = tasks || currentTasks || {};
  const track = document.getElementById('pipeline-track');
  if (!track) return;

  track.innerHTML = phases.map(function(p) {
    const taskKey = 'phase-' + p.phase;
    const task = tasks[taskKey];
    const taskStatus = task ? ((typeof task === 'object' && task !== null) ? task.status : task) : null;
    const isRunning = taskStatus === 'running';

    let badgeClass = 'badge-' + p.status;
    if (isRunning) {
      badgeClass = 'badge-running';
    }

    const countText = p.total ? (p.count + '/' + p.total) : p.count;
    let progressHtml = '';
    if (p.total && p.total > 0) {
      const pct = Math.round((p.count / p.total) * 100);
      progressHtml = '<div class="phase-progress"><div class="phase-progress-fill" style="width:' + pct + '%"></div></div>';
    }

    let actionBtnHtml = '';
    if (isRunning) {
      actionBtnHtml = '<div style="display:flex;gap:6px;align-items:center;justify-content:center;">' +
        '<button class="btn btn-running" disabled title="Executando em segundo plano"><span class="spinner-dot"></span> ⏳ Executando...</button>' +
        '<button class="btn btn-stop" onclick="stopTask(\'' + taskKey + '\')" title="Parar processo imediatamente">⏹</button>' +
        '</div>';
    } else {
      actionBtnHtml = '<button class="btn btn-run" onclick="runPhase(' + p.phase + ')">▶ Run</button>';
    }

    let detailText = p.detail;
    if (isRunning && typeof task === 'object' && task && task.last_log) {
      const snippet = task.last_log.length > 35 ? (task.last_log.slice(0, 32) + '…') : task.last_log;
      detailText = '<span style="color:var(--accent-amber);" title="' + esc(task.last_log) + '">' + esc(snippet) + '</span>';
    }

    return '' +
      '<div class="phase-node' + (isRunning ? ' phase-node-running' : '') + '">' +
        '<div class="phase-icon">' + p.icon + '</div>' +
        '<div class="phase-name">' + p.name + '</div>' +
        '<div class="phase-count">' + countText + '</div>' +
        '<div class="phase-detail">' + detailText + '</div>' +
        progressHtml +
        '<span class="phase-badge ' + badgeClass + '"></span>' +
        '<div class="phase-actions">' +
          actionBtnHtml +
        '</div>' +
      '</div>';
  }).join('');
}

// ── Tab Switching ──────────────────────────────────
function switchTab(name) {
  currentTab = name;

  document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
  const activeTabBtn = document.querySelector('.tab[data-tab="' + name + '"]');
  if (activeTabBtn) activeTabBtn.classList.add('active');

  document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
  const activeContent = document.getElementById('tab-' + name);
  if (activeContent) activeContent.classList.add('active');

  loadCurrentTab();
}

async function loadCurrentTab() {
  switch (currentTab) {
    case 'gallery': return loadGallery();
    case 'queue': return loadQueue();
    case 'qc': return loadQC();
    case 'matrix': return loadMatrix();
    case 'agencies': return loadAgencies();
    case 'timeline': return loadTimeline();
    case 'backup': return loadBackup();
    case 'seasonal': return loadSeasonal();
    case 'daemon': return loadDaemon();
  }
}

// ── Gallery ────────────────────────────────────────
async function loadGallery() {
  const res = await fetch(API + '/api/images?filter=' + currentImageFilter);
  const data = await res.json();

  document.getElementById('gallery-stat').textContent =
    data.total + ' imagens | ' + data.cataloged + ' catalogados | ' + data.uncataloged + ' pendentes';

  const grid = document.getElementById('gallery-grid');
  if (!data.images || data.images.length === 0) {
    grid.innerHTML = '<div class="loading">Nenhuma imagem encontrada</div>';
    return;
  }

  grid.innerHTML = data.images.map(function(img) {
    const badge = img.is_cataloged
      ? '<span class="gallery-item-badge badge-cataloged">✓ IPTC</span>'
      : '<span class="gallery-item-badge badge-uncataloged">⏳</span>';
    const uploadBadge = (img.uploaded_agencies && img.uploaded_agencies.length > 0)
      ? '<span class="gallery-item-badge" style="right:auto; left:8px; background:rgba(6,182,212,0.9); color:#fff; font-size:0.65rem; padding:2px 6px; border-radius:4px; font-weight:600;">🚀 ' + img.uploaded_agencies.length + ' enviada' + (img.uploaded_agencies.length > 1 ? 's' : '') + '</span>'
      : '';
    const title = img.title || img.filename;
    return '' +
      '<div class="gallery-item" onclick="openImageModal(\'' + esc(img.filename) + '\')">' +
        '<img src="/api/images/' + encodeURIComponent(img.filename) + '/thumb" alt="' + esc(title) + '" loading="lazy">' +
        badge +
        uploadBadge +
        '<div class="gallery-item-overlay">' +
          '<div class="gallery-item-title">' + esc(title) + '</div>' +
          '<div class="gallery-item-size">' + img.size_mb + ' MB</div>' +
        '</div>' +
      '</div>';
  }).join('');
}

function filterImages(f) {
  currentImageFilter = f;
  document.querySelectorAll('#tab-gallery .filter-btn').forEach(function(b) { b.classList.remove('active'); });
  if (event && event.target) event.target.classList.add('active');
  loadGallery();
}

// ── Image Modal ────────────────────────────────────
async function openImageModal(filename) {
  const overlay = document.getElementById('modal-overlay');
  document.getElementById('modal-img').src = '/api/images/' + encodeURIComponent(filename);
  document.getElementById('modal-title').textContent = filename;
  document.getElementById('modal-meta').innerHTML = '<div class="loading">Carregando metadados…</div>';
  overlay.classList.add('open');

  try {
    const res = await fetch('/api/images/' + encodeURIComponent(filename) + '/meta');
    const meta = await res.json();
    renderModalMeta(meta);
  } catch (e) {
    document.getElementById('modal-meta').innerHTML = '<div class="loading">Erro ao carregar metadados</div>';
  }
}

function renderModalMeta(meta) {
  const div = document.getElementById('modal-meta');
  let html = '';

  if (meta.iptc && meta.iptc.title) {
    document.getElementById('modal-title').textContent = meta.iptc.title;
  }

  if (meta.iptc && meta.iptc.caption) {
    html += '' +
      '<div class="meta-group">' +
        '<div class="meta-group-title">Caption (IPTC)</div>' +
        '<div class="meta-group-value">' + esc(meta.iptc.caption) + '</div>' +
      '</div>';
  }

  if (meta.exif && meta.exif.description && (!meta.iptc || meta.exif.description !== meta.iptc.title)) {
    html += '' +
      '<div class="meta-group">' +
        '<div class="meta-group-title">Description (EXIF)</div>' +
        '<div class="meta-group-value">' + esc(meta.exif.description) + '</div>' +
      '</div>';
  }

  const kws = (meta.iptc && meta.iptc.keywords) || (meta.exif && meta.exif.xp_keywords ? meta.exif.xp_keywords.split(',') : null);
  if (kws && kws.length > 0) {
    html += '' +
      '<div class="meta-group">' +
        '<div class="meta-group-title">Keywords (' + kws.length + ')</div>' +
        '<div class="keyword-tags">' +
          kws.map(function(k) { return '<span class="keyword-tag">' + esc(k.trim()) + '</span>'; }).join('') +
        '</div>' +
      '</div>';
  }

  if (meta.uploaded_agencies && meta.uploaded_agencies.length > 0) {
    html += '' +
      '<div class="meta-group">' +
        '<div class="meta-group-title">Enviado para Agências (' + meta.uploaded_agencies.length + ')</div>' +
        '<div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:4px;">' +
          meta.uploaded_agencies.map(function(a) {
            return '<span style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.3); font-weight:600; font-size:0.75rem; padding:3px 8px; border-radius:4px;">✓ ' + esc(a.toUpperCase()) + '</span>';
          }).join('') +
        '</div>' +
      '</div>';
  }

  if (!html) {
    html = '<div class="meta-group"><div class="meta-group-value" style="color:var(--text-muted)">Nenhum metadado IPTC/EXIF encontrado</div></div>';
  }

  div.innerHTML = html;
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.getElementById('modal-img').src = '';
}

// ── Queue ──────────────────────────────────────────
let selectedPromptHashes = new Set();
let currentQueueItems = [];

async function loadQueue() {
  const res = await fetch(API + '/api/prompts?filter=' + currentQueueFilter + '&per_page=200');
  const data = await res.json();
  currentQueueItems = data.items || [];

  const gen = currentQueueItems.filter(function(i) { return i.status === 'generated'; }).length;
  const pend = currentQueueItems.filter(function(i) { return i.status === 'pending'; }).length;
  document.getElementById('queue-stat').textContent =
    gen + ' gerados | ' + pend + ' pendentes | ' + data.total + ' total';

  const tbody = document.getElementById('queue-tbody');
  if (!currentQueueItems || currentQueueItems.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Nenhum prompt encontrado</td></tr>';
    updateSelectedUI();
    return;
  }

  tbody.innerHTML = currentQueueItems.map(function(p) {
    const chipClass = p.status === 'generated' ? 'chip-generated' : 'chip-pending';
    const statusIcon = p.status === 'generated' ? '✅' : '⏳';
    const date = p.generated_at ? new Date(p.generated_at).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'short'}) : '—';
    const hash = p.full_hash || p.prompt_hash;
    const isChecked = selectedPromptHashes.has(hash);
    const isPending = p.status === 'pending';

    let actionBtn = '';
    if (isPending) {
      actionBtn = '<button class="btn btn-sm btn-success" style="padding:2px 8px;font-size:0.68rem;" data-hash="' + esc(hash) + '" onclick="markSinglePromptGenerated(this.dataset.hash)" title="Marcar este prompt individual como gerado">✓ Gerado</button>';
    } else {
      actionBtn = '<button class="btn btn-sm btn-warning" style="padding:2px 8px;font-size:0.68rem;" data-hash="' + esc(hash) + '" onclick="markSinglePromptPending(this.dataset.hash)" title="Reverter este prompt para status pendente">⏳ Pendente</button>';
    }

    return '' +
      '<tr>' +
        '<td style="text-align:center;">' +
          '<input type="checkbox" class="prompt-select-checkbox prompt-row-checkbox" data-hash="' + esc(hash) + '" ' +
            (isChecked ? 'checked ' : '') +
            'onchange="togglePromptSelect(this.dataset.hash, this.checked)">' +
        '</td>' +
        '<td class="mono" title="' + esc(hash) + '">' + esc(p.prompt_hash) + '</td>' +
        '<td>' + esc(p.concept || '—') + '</td>' +
        '<td class="mono">' + esc(p.source_id || '—') + '</td>' +
        '<td><span class="status-chip ' + chipClass + '">' + statusIcon + ' ' + p.status + '</span></td>' +
        '<td class="mono">' + date + '</td>' +
        '<td style="text-align:center;">' + actionBtn + '</td>' +
      '</tr>';
  }).join('');

  updateSelectedUI();
}

function togglePromptSelect(hash, isChecked) {
  if (isChecked) {
    selectedPromptHashes.add(hash);
  } else {
    selectedPromptHashes.delete(hash);
  }
  updateSelectedUI();
}

function toggleSelectAll(isChecked) {
  if (isChecked) {
    currentQueueItems.forEach(function(p) {
      const hash = p.full_hash || p.prompt_hash;
      selectedPromptHashes.add(hash);
    });
  } else {
    selectedPromptHashes.clear();
  }

  document.querySelectorAll('.prompt-row-checkbox').forEach(function(cb) {
    const h = cb.getAttribute('data-hash');
    cb.checked = selectedPromptHashes.has(h);
  });

  updateSelectedUI();
}

function updateSelectedUI() {
  const count = selectedPromptHashes.size;
  const countEl = document.getElementById('selected-count');
  if (countEl) countEl.textContent = count;

  const countPendingEl = document.getElementById('selected-pending-count');
  if (countPendingEl) countPendingEl.textContent = count;

  const btnMark = document.getElementById('btn-mark-selected');
  if (btnMark) {
    btnMark.disabled = count === 0;
  }

  const btnMarkPending = document.getElementById('btn-mark-selected-pending');
  if (btnMarkPending) {
    btnMarkPending.disabled = count === 0;
  }

  const selectAllCb = document.getElementById('select-all-prompts');
  if (selectAllCb) {
    if (currentQueueItems.length > 0 && currentQueueItems.every(function(p) { return selectedPromptHashes.has(p.full_hash || p.prompt_hash); })) {
      selectAllCb.checked = true;
      selectAllCb.indeterminate = false;
    } else if (count > 0) {
      selectAllCb.checked = false;
      selectAllCb.indeterminate = true;
    } else {
      selectAllCb.checked = false;
      selectAllCb.indeterminate = false;
    }
  }
}

async function markSelectedGenerated() {
  if (selectedPromptHashes.size === 0) return;
  const count = selectedPromptHashes.size;
  if (!confirm('Deseja marcar os ' + count + ' prompt(s) selecionado(s) como gerado(s)?')) return;

  try {
    const res = await fetch(API + '/api/prompts/mark-generated', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hashes: Array.from(selectedPromptHashes) }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('✅ ' + (data.message || (count + ' prompts marcados como gerados!')));
      selectedPromptHashes.clear();
      await refreshAll();
    } else {
      showToast('❌ ' + (data.message || 'Erro ao marcar prompts'));
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

async function markAllPendingGenerated() {
  if (!confirm('Deseja marcar TODOS os prompts pendentes da fila como gerados?')) return;

  try {
    const res = await fetch(API + '/api/prompts/mark-generated', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ all_pending: true }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('✅ ' + (data.message || 'Todos os prompts pendentes foram marcados como gerados!'));
      selectedPromptHashes.clear();
      await refreshAll();
    } else {
      showToast('❌ ' + (data.message || 'Erro ao marcar prompts'));
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

async function markSinglePromptGenerated(hash) {
  try {
    const res = await fetch(API + '/api/prompts/mark-generated', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hashes: [hash] }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('✅ Prompt marcado como gerado!');
      selectedPromptHashes.delete(hash);
      await refreshAll();
    } else {
      showToast('❌ ' + (data.message || 'Erro ao marcar prompt'));
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

async function markSelectedPending() {
  if (selectedPromptHashes.size === 0) return;
  const count = selectedPromptHashes.size;
  if (!confirm('Deseja marcar os ' + count + ' prompt(s) selecionado(s) como PENDENTE(S)?')) return;

  try {
    const res = await fetch(API + '/api/prompts/mark-pending', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hashes: Array.from(selectedPromptHashes) }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('⏳ ' + (data.message || (count + ' prompts marcados como pendentes!')));
      selectedPromptHashes.clear();
      await refreshAll();
    } else {
      showToast('❌ ' + (data.message || 'Erro ao reverter prompts'));
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

async function markSinglePromptPending(hash) {
  try {
    const res = await fetch(API + '/api/prompts/mark-pending', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hashes: [hash] }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('⏳ Prompt revertido para pendente!');
      selectedPromptHashes.delete(hash);
      await refreshAll();
    } else {
      showToast('❌ ' + (data.message || 'Erro ao reverter status'));
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

async function markAllGeneratedPending() {
  if (!confirm('Deseja reverter TODOS os prompts gerados da fila para PENDENTE?')) return;

  try {
    const res = await fetch(API + '/api/prompts/mark-pending', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ all_generated: true }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('⏳ ' + (data.message || 'Todos os prompts foram revertidos para pendentes!'));
      selectedPromptHashes.clear();
      await refreshAll();
    } else {
      showToast('❌ ' + (data.message || 'Erro ao reverter prompts'));
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

function filterQueue(f) {
  currentQueueFilter = f;
  document.querySelectorAll('#tab-queue .filter-btn').forEach(function(b) { b.classList.remove('active'); });
  if (event && event.target) event.target.classList.add('active');
  loadQueue();
}

// ── Distribution Matrix ──────────────────────────
let matrixData = null;
let currentMatrixFilter = 'all';
let matrixSearchQuery = '';

async function loadMatrix() {
  const tbody = document.getElementById('matrix-tbody');
  try {
    const res = await fetch(API + '/api/matrix');
    if (!res.ok) throw new Error('Falha ao carregar matriz: ' + res.status);
    matrixData = await res.json();
    renderMatrix();
  } catch (err) {
    console.error('Matrix error:', err);
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="10" class="loading">❌ Erro ao carregar matriz: ' + esc(err.message) + '</td></tr>';
    }
  }
}

function filterMatrix(mode) {
  currentMatrixFilter = mode;
  document.querySelectorAll('#tab-matrix .filter-btn').forEach(function(b) { b.classList.remove('active'); });
  const activeBtn = document.getElementById('matrix-filter-' + mode);
  if (activeBtn) activeBtn.classList.add('active');
  renderMatrix();
}

function onMatrixSearch(query) {
  matrixSearchQuery = (query || '').toLowerCase().trim();
  renderMatrix();
}

function renderMatrix() {
  if (!matrixData) return;

  const thead = document.getElementById('matrix-thead');
  const tbody = document.getElementById('matrix-tbody');
  const statEl = document.getElementById('matrix-stat');

  const agencies = matrixData.agencies || [];
  let items = matrixData.items || [];

  // Filter items
  if (matrixSearchQuery) {
    items = items.filter(function(it) {
      return (it.filename && it.filename.toLowerCase().indexOf(matrixSearchQuery) !== -1) ||
             (it.title && it.title.toLowerCase().indexOf(matrixSearchQuery) !== -1);
    });
  }

  if (currentMatrixFilter === 'pending') {
    items = items.filter(function(it) {
      return it.pending_configured > 0 || it.uploaded_count < agencies.length;
    });
  } else if (currentMatrixFilter === 'done') {
    items = items.filter(function(it) {
      return it.uploaded_count === agencies.length || (it.uploaded_count > 0 && it.pending_configured === 0);
    });
  }

  // Update stat label
  const totalImgs = matrixData.summary ? matrixData.summary.total_images : 0;
  const totalUploads = matrixData.summary ? matrixData.summary.total_uploads : 0;
  const totalSlots = matrixData.summary ? matrixData.summary.total_slots : 0;
  const pct = totalSlots > 0 ? Math.round((totalUploads / totalSlots) * 100) : 0;
  if (statEl) {
    statEl.textContent = items.length + '/' + totalImgs + ' fotos | ' + totalUploads + ' uploads concluídos (' + pct + '%)';
  }

  // Render THEAD with Agency Quick Action Buttons
  let headerHtml = '<tr>' +
    '<th style="width:50px; text-align:center;">Foto</th>' +
    '<th style="min-width:220px;">Arquivo & Título</th>';

  agencies.forEach(function(ag) {
    const badge = ag.configured
      ? '<span class="badge-configured">Configurado</span>'
      : '<span class="badge-unconfigured">Não config.</span>';

    headerHtml += '' +
      '<th>' +
        '<div class="matrix-agency-header">' +
          '<div class="matrix-agency-name">' +
            '<span>' + esc(ag.name) + '</span> ' + badge +
          '</div>' +
          '<div class="matrix-header-actions">' +
            '<button class="btn-mini" onclick="batchSetMatrixAgency(\'' + ag.key + '\', \'mark_all\')" title="Marcar todos como enviados para ' + esc(ag.name) + '">✓ Todos</button>' +
            '<button class="btn-mini btn-mini-danger" onclick="batchSetMatrixAgency(\'' + ag.key + '\', \'unmark_all\')" title="Desmarcar todos de ' + esc(ag.name) + '">✕ Limpar</button>' +
          '</div>' +
        '</div>' +
      '</th>';
  });

  headerHtml += '<th style="text-align:center; width:100px;">Progresso</th></tr>';
  if (thead) thead.innerHTML = headerHtml;

  // Render TBODY
  if (items.length === 0) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="' + (agencies.length + 3) + '" class="loading">Nenhuma foto encontrada para os filtros selecionados</td></tr>';
    return;
  }

  let bodyHtml = '';
  items.forEach(function(it) {
    const thumbUrl = API + '/api/images/' + encodeURIComponent(it.filename) + '/thumb';
    const fullImgUrl = API + '/api/images/' + encodeURIComponent(it.filename);

    bodyHtml += '<tr>';
    bodyHtml += '<td style="text-align:center;"><img src="' + thumbUrl + '" class="matrix-thumb" alt="Thumb" onclick="openModal(\'' + fullImgUrl + '\', \'' + esc(it.title) + '\', \'' + esc(it.filename) + '\')"></td>';
    bodyHtml += '<td>' +
      '<div style="font-weight:600; color:var(--text-primary); font-size:0.83rem;">' + esc(it.title) + '</div>' +
      '<div style="font-family:var(--font-mono); font-size:0.72rem; color:var(--text-muted); margin-top:2px;">' +
        esc(it.filename) + ' • ' + it.size_mb + ' MB ' + (it.is_cataloged ? '• <span style="color:#10b981;">✓ IPTC</span>' : '') +
      '</div>' +
    '</td>';

    agencies.forEach(function(ag) {
      const plat = it.platforms[ag.key] || { uploaded: false, timestamp: null };
      const isChecked = plat.uploaded ? 'checked' : '';
      const dotClass = plat.uploaded ? 'status-dot-uploaded' : 'status-dot-pending';
      const tooltip = plat.uploaded
        ? ('Enviado em ' + (plat.timestamp || 'data não informada'))
        : ('Pendente de envio para ' + ag.name);

      bodyHtml += '<td>' +
        '<div class="matrix-cell-status-wrap" title="' + tooltip + '">' +
          '<input type="checkbox" class="matrix-checkbox" ' + isChecked + ' ' +
            'onchange="toggleMatrixCell(\'' + esc(it.filename) + '\', \'' + ag.key + '\', this.checked)">' +
          '<span class="' + dotClass + '"></span>' +
        '</div>' +
      '</td>';
    });

    const progPct = Math.round((it.uploaded_count / agencies.length) * 100);
    const progColor = progPct === 100 ? '#10b981' : (progPct > 0 ? '#06b6d4' : 'var(--text-muted)');

    bodyHtml += '<td style="text-align:center;">' +
      '<span style="font-weight:700; color:' + progColor + '; font-size:0.82rem;">' + it.uploaded_count + '/' + agencies.length + '</span>' +
      '<div style="font-size:0.68rem; color:var(--text-muted);">' + progPct + '%</div>' +
    '</td>';
    bodyHtml += '</tr>';
  });

  if (tbody) tbody.innerHTML = bodyHtml;
}

async function toggleMatrixCell(filename, agency, uploaded) {
  try {
    const res = await fetch(API + '/api/matrix/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: filename, agency: agency, uploaded: uploaded })
    });
    const data = await res.json();
    if (!data.success) {
      showToast('❌ Erro ao atualizar status');
      await loadMatrix();
    } else {
      showToast((uploaded ? '✅ Marcado como enviado' : '⚪ Marcado como pendente') + ': ' + agency);
      if (matrixData && matrixData.items) {
        const item = matrixData.items.find(function(i) { return i.filename === filename; });
        if (item) {
          if (!item.platforms[agency]) item.platforms[agency] = {};
          item.platforms[agency].uploaded = uploaded;
          item.uploaded_count = Object.values(item.platforms).filter(function(p) { return p.uploaded; }).length;
          const totalUploads = matrixData.items.reduce(function(acc, i) { return acc + i.uploaded_count; }, 0);
          if (matrixData.summary) matrixData.summary.total_uploads = totalUploads;
          renderMatrix();
        }
      }
    }
  } catch (err) {
    showToast('❌ Erro de conexão: ' + err.message);
    await loadMatrix();
  }
}

async function batchSetMatrixAgency(agency, action) {
  const isMark = action === 'mark_all';
  const confirmMsg = isMark
    ? ('Deseja marcar TODAS as fotos como enviadas para ' + agency.toUpperCase() + '?')
    : ('Deseja desmarcar TODAS as fotos de ' + agency.toUpperCase() + ' (definir como pendentes)?');

  if (!confirm(confirmMsg)) return;

  try {
    showToast('⏳ Atualizando coluna ' + agency + '...');
    const res = await fetch(API + '/api/matrix/batch-set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agency: agency, action: action })
    });
    const data = await res.json();
    if (data.success) {
      showToast('✅ ' + data.updated_count + ' fotos atualizadas para ' + agency);
      await loadMatrix();
    } else {
      showToast('❌ Falha ao atualizar em lote');
    }
  } catch (err) {
    showToast('❌ Erro: ' + err.message);
  }
}

async function triggerMatrixUpload() {
  const taskKey = 'phase-5';
  const currentTask = currentTasks[taskKey];
  const isRunning = currentTask && ((typeof currentTask === 'object' && currentTask !== null) ? currentTask.status === 'running' : currentTask === 'running');
  if (isRunning) {
    showToast('⚠️ Distribuição já está em execução.');
    return;
  }

  if (!confirm('Iniciar upload automático das fotos pendentes para Dreamstime e 123RF?')) {
    return;
  }

  showToast('🚀 Disparando upload dos pendentes...');
  try {
    const res = await fetch(API + '/api/matrix/upload-pending', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('✅ Upload iniciado em segundo plano!');
      pollTasksOnly();
    } else {
      showToast('❌ ' + (data.message || 'Falha ao iniciar upload'));
    }
  } catch (err) {
    showToast('❌ Erro: ' + err.message);
  }
}

// ── Agencies ───────────────────────────────────────
async function loadAgencies() {
  const res = await fetch(API + '/api/agencies');
  const agencies = await res.json();
  const phase5Task = currentTasks['phase-5'];
  const isPhase5Running = phase5Task && ((typeof phase5Task === 'object' && phase5Task !== null) ? phase5Task.status === 'running' : phase5Task === 'running');

  const tbody = document.getElementById('agencies-tbody');
  tbody.innerHTML = agencies.map(function(a) {
    const statusChip = a.configured
      ? '<span class="status-chip chip-configured">🟢 Configurado</span>'
      : '<span class="status-chip chip-not-configured">⚪ Não configurado</span>';
    const lastUpload = a.last_upload ? new Date(a.last_upload).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'short'}) : '—';
    let actions = '<span style="color:var(--text-muted);font-size:0.7rem">Configure no .env</span>';
    if (a.configured) {
      if (isPhase5Running) {
        actions = '<button class="btn btn-running" disabled><span class="spinner-dot"></span> Enviando...</button>';
      } else {
        actions = '<button class="btn btn-run" onclick="runUpload(\'' + a.key + '\')">Enviar</button>';
      }
    }
    const portalLink = a.portal_url
      ? '<a href="' + a.portal_url + '" target="_blank" rel="noopener noreferrer" class="btn btn-sm" style="text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-size:0.75rem; padding:4px 9px; background:rgba(6,182,212,0.12); color:var(--accent-cyan); border:1px solid rgba(6,182,212,0.3); border-radius:4px;">🔗 Acessar Portal ↗</a>'
      : '<span style="color:var(--text-muted); font-size:0.75rem;">—</span>';

    return '' +
      '<tr>' +
        '<td><strong>' + esc(a.name) + '</strong></td>' +
        '<td class="mono">' + a.protocol + '</td>' +
        '<td>' + statusChip + '</td>' +
        '<td class="mono">' + a.uploads + '</td>' +
        '<td class="mono">' + lastUpload + '</td>' +
        '<td>' + portalLink + '</td>' +
        '<td>' + actions + '</td>' +
      '</tr>';
  }).join('');
}

// ── Timeline ───────────────────────────────────────
async function loadTimeline() {
  const res = await fetch(API + '/api/timeline');
  const events = await res.json();

  const feed = document.getElementById('timeline-feed');
  if (!events || events.length === 0) {
    feed.innerHTML = '<div class="loading">Nenhum evento registrado</div>';
    return;
  }

  feed.innerHTML = events.map(function(e) {
    const time = e.timestamp ? new Date(e.timestamp).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'medium'}) : '—';
    return '' +
      '<div class="timeline-item">' +
        '<div class="timeline-icon">' + e.icon + '</div>' +
        '<div class="timeline-body">' +
          '<div class="timeline-msg">' + esc(e.message) + '</div>' +
          '<div class="timeline-time">' + time + '</div>' +
        '</div>' +
      '</div>';
  }).join('');
}

// ── Backup ─────────────────────────────────────────
async function loadBackup() {
  const res = await fetch(API + '/api/backup');
  const b = await res.json();
  const backupTask = currentTasks['backup'];
  const isBackupRunning = backupTask && ((typeof backupTask === 'object' && backupTask !== null) ? backupTask.status === 'running' : backupTask === 'running');

  const card = document.getElementById('backup-card');
  const statusText = b.configured ? ('🟢 Ativo (' + (b.mode || 'unknown') + ')') : '🔴 Não configurado';
  const lastSyncText = b.last_sync ? new Date(b.last_sync).toLocaleString('pt-BR') : '—';

  let actionBtnHtml = '';
  if (isBackupRunning) {
    actionBtnHtml = '<button class="btn btn-running" disabled><span class="spinner-dot"></span> ⏳ Sincronizando...</button>';
  } else {
    actionBtnHtml = '<button class="btn btn-run ' + (b.configured ? '' : 'btn-disabled') + '" onclick="runBackupSync()">☁️ Sync Now</button>';
  }

  card.innerHTML = '' +
    '<div class="backup-row">' +
      '<span class="backup-label">Status</span>' +
      '<span class="backup-value">' + statusText + '</span>' +
    '</div>' +
    '<div class="backup-row">' +
      '<span class="backup-label">Assets Sincronizados</span>' +
      '<span class="backup-value">' + b.synced_count + '</span>' +
    '</div>' +
    '<div class="backup-row">' +
      '<span class="backup-label">Último Sync</span>' +
      '<span class="backup-value">' + lastSyncText + '</span>' +
    '</div>' +
    '<div class="backup-actions">' +
      actionBtnHtml +
    '</div>';
}

// ── Seasonal Radar ─────────────────────────────────
async function loadSeasonal() {
  const res = await fetch(API + '/api/seasonal');
  const data = await res.json();
  const phase1Task = currentTasks['phase-1'];
  const isPhase1Running = phase1Task && ((typeof phase1Task === 'object' && phase1Task !== null) ? phase1Task.status === 'running' : phase1Task === 'running');

  const sub = document.getElementById('seasonal-meta-sub');
  if (sub) {
    sub.textContent = 'Alvo de Compra B2B: ' + data.target_procurement_date + ' (' + data.target_quarter + ' - Mês ' + data.target_month + ') • Tema: ' + data.macro_theme;
  }

  const grid = document.getElementById('seasonal-grid');
  if (!data.recommended_niches || data.recommended_niches.length === 0) {
    grid.innerHTML = '<div class="loading">Nenhuma oportunidade calculada</div>';
    return;
  }

  grid.innerHTML = data.recommended_niches.map(function(n) {
    const mineBtnHtml = isPhase1Running
      ? '<button class="seasonal-btn-mine btn-running" disabled><span class="spinner-dot"></span> ⏳ Mineração em andamento...</button>'
      : '<button class="seasonal-btn-mine" onclick="mineNiche(\'' + esc(n.query) + '\')">🚀 Minerar este Nicho (Fase 1)</button>';

    return '' +
      '<div class="seasonal-card">' +
        '<div>' +
          '<div class="seasonal-card-header">' +
            '<h3 class="seasonal-card-title">' + esc(n.name) + '</h3>' +
            '<span class="badge-blue-ocean">🟢 Blue Ocean</span>' +
          '</div>' +
          '<p class="seasonal-card-rationale">' + esc(n.rationale) + '</p>' +
          '<div class="seasonal-meta-block">' +
            '<div class="seasonal-meta-line">' +
              '<span class="seasonal-meta-key">Layout:</span>' +
              '<span class="seasonal-meta-val">' + esc(n.suggested_layout) + '</span>' +
            '</div>' +
            '<div class="seasonal-meta-line">' +
              '<span class="seasonal-meta-key">Compradores:</span>' +
              '<span class="seasonal-meta-val" style="color:var(--text-secondary);font-family:var(--font-sans);">' + esc(n.target_buyers.join(', ')) + '</span>' +
            '</div>' +
            '<div class="seasonal-meta-line">' +
              '<span class="seasonal-meta-key">Query:</span>' +
              '<span class="seasonal-meta-val">' + esc(n.query) + '</span>' +
            '</div>' +
          '</div>' +
        '</div>' +
        mineBtnHtml +
      '</div>';
  }).join('');
}

async function mineNiche(query) {
  const taskKey = 'phase-1';
  const currentTask = currentTasks[taskKey];
  const isRunning = currentTask && ((typeof currentTask === 'object' && currentTask !== null) ? currentTask.status === 'running' : currentTask === 'running');
  if (isRunning) {
    showToast('⚠️ Fase 1 (Olheiro) já está em execução.');
    return;
  }

  if (!confirm('Iniciar mineração da Fase 1 para o nicho:\n"' + query + '"?')) return;
  currentTasks[taskKey] = {
    task_id: taskKey,
    phase: 1,
    status: 'running',
    started_at: new Date().toISOString(),
    logs: ['Minerando nicho: ' + query],
    last_log: 'Minerando nicho: ' + query,
  };
  previousTasks[taskKey] = { status: 'running' };
  if (currentPhases.length > 0) {
    renderPipeline(currentPhases, currentTasks);
  }
  if (currentTab === 'seasonal') loadSeasonal();
  updateTaskPolling();
  showToast('🚀 Mineração iniciada para: ' + query);

  try {
    const res = await fetch(API + '/api/run-phase/1?query=' + encodeURIComponent(query) + '&mode=search', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('⏳ Mineração da Fase 1 em andamento…');
    } else {
      showToast('❌ ' + (data.message || 'Falha ao iniciar'));
      if (!data.message || !data.message.includes('already running')) {
        delete currentTasks[taskKey];
        delete previousTasks[taskKey];
        if (currentPhases.length > 0) {
          renderPipeline(currentPhases, currentTasks);
        }
        if (currentTab === 'seasonal') loadSeasonal();
      }
      pollTasksOnly();
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
    delete currentTasks[taskKey];
    delete previousTasks[taskKey];
    if (currentPhases.length > 0) {
      renderPipeline(currentPhases, currentTasks);
    }
    if (currentTab === 'seasonal') loadSeasonal();
    updateTaskPolling();
  }
}

// ── Actions ────────────────────────────────────────
async function runPhase(n) {
  const taskKey = 'phase-' + n;
  const currentTask = currentTasks[taskKey];
  const isRunning = currentTask && ((typeof currentTask === 'object' && currentTask !== null) ? currentTask.status === 'running' : currentTask === 'running');
  if (isRunning) {
    showToast('⚠️ Fase ' + n + ' já está em execução.');
    return;
  }

  // Phase 2 check: Inform user if all prompts are already generated or no trends
  if (n === 2 && currentKpis) {
    if (currentKpis.trends === 0) {
      const proceed = confirm(
        '⚠️ Nenhuma tendência minerada encontrada (0 trends).\n\n' +
        'Recomenda-se executar a Fase 1 (Olheiro) antes de gerar prompts.\n\n' +
        'Deseja executar a Fase 2 mesmo assim?'
      );
      if (!proceed) return;
    } else if (currentKpis.trends > 0 && currentKpis.prompts_analyzed >= currentKpis.trends) {
      const proceed = confirm(
        'ℹ️ Todos os ' + currentKpis.prompts_total + ' prompts já foram gerados (' + currentKpis.prompts_analyzed + ' tendências analisadas).\n\n' +
        'Deseja re-executar a verificação da Fase 2?'
      );
      if (!proceed) return;
    } else {
      if (!confirm('Iniciar Fase ' + n + '?')) return;
    }
  } else if (n === 3 && currentKpis) {
    if (currentKpis.queue_pending === 0 && currentKpis.queue_total > 0) {
      const proceed = confirm(
        'ℹ️ Todos os ' + currentKpis.queue_total + ' prompts da fila já foram gerados em imagens 4K (0 pendentes).\n\n' +
        'Deseja executar a Fase 3 mesmo assim?'
      );
      if (!proceed) return;
    } else {
      if (!confirm('Iniciar Fase ' + n + '?')) return;
    }
  } else {
    if (!confirm('Iniciar Fase ' + n + '?')) return;
  }

  // Optimistic UI state
  currentTasks[taskKey] = {
    task_id: taskKey,
    phase: n,
    status: 'running',
    started_at: new Date().toISOString(),
    logs: ['Iniciando processo...'],
    last_log: 'Iniciando processo...',
  };
  previousTasks[taskKey] = { status: 'running' };
  if (currentPhases.length > 0) {
    renderPipeline(currentPhases, currentTasks);
  }
  updateTaskPolling();

  showToast('🚀 Iniciando Fase ' + n + '…');

  try {
    const res = await fetch(API + '/api/run-phase/' + n, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('⏳ Fase ' + n + ' em execução em segundo plano…');
    } else {
      showToast('❌ ' + (data.message || 'Falha ao iniciar'));
      if (!data.message || !data.message.includes('already running')) {
        delete currentTasks[taskKey];
        delete previousTasks[taskKey];
        if (currentPhases.length > 0) {
          renderPipeline(currentPhases, currentTasks);
        }
      }
      pollTasksOnly();
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
    delete currentTasks[taskKey];
    delete previousTasks[taskKey];
    if (currentPhases.length > 0) {
      renderPipeline(currentPhases, currentTasks);
    }
    updateTaskPolling();
  }
}

async function runUpload(agency) {
  const taskKey = 'phase-5';
  const currentTask = currentTasks[taskKey];
  const isRunning = currentTask && ((typeof currentTask === 'object' && currentTask !== null) ? currentTask.status === 'running' : currentTask === 'running');
  if (isRunning) {
    showToast('⚠️ Upload para agências (Fase 5) já está em execução.');
    return;
  }

  if (!confirm('Enviar assets para ' + agency + '?')) return;
  showToast('🚀 Upload para ' + agency + ' iniciado… (via Phase 5)');

  currentTasks[taskKey] = {
    task_id: taskKey,
    phase: 5,
    status: 'running',
    started_at: new Date().toISOString(),
    logs: ['Iniciando upload para ' + agency],
    last_log: 'Iniciando upload para ' + agency,
  };
  previousTasks[taskKey] = { status: 'running' };
  if (currentPhases.length > 0) {
    renderPipeline(currentPhases, currentTasks);
  }
  if (currentTab === 'agencies') loadAgencies();
  updateTaskPolling();

  try {
    const res = await fetch(API + '/api/run-phase/5?platform=' + encodeURIComponent(agency), { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('⏳ Upload da Fase 5 (' + agency + ') em execução…');
    } else {
      showToast('❌ ' + (data.message || 'Falha no upload'));
      if (!data.message || !data.message.includes('already running')) {
        delete currentTasks[taskKey];
        delete previousTasks[taskKey];
        if (currentPhases.length > 0) {
          renderPipeline(currentPhases, currentTasks);
        }
        if (currentTab === 'agencies') loadAgencies();
      }
      pollTasksOnly();
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
    delete currentTasks[taskKey];
    delete previousTasks[taskKey];
    if (currentPhases.length > 0) {
      renderPipeline(currentPhases, currentTasks);
    }
    if (currentTab === 'agencies') loadAgencies();
    updateTaskPolling();
  }
}

async function runBackupSync() {
  const taskKey = 'backup';
  const currentTask = currentTasks[taskKey];
  const isRunning = currentTask && ((typeof currentTask === 'object' && currentTask !== null) ? currentTask.status === 'running' : currentTask === 'running');
  if (isRunning) {
    showToast('⚠️ Backup já está em execução.');
    return;
  }

  currentTasks[taskKey] = {
    task_id: taskKey,
    phase: null,
    status: 'running',
    started_at: new Date().toISOString(),
    logs: ['Iniciando backup em nuvem...'],
    last_log: 'Iniciando backup em nuvem...',
  };
  previousTasks[taskKey] = { status: 'running' };
  if (currentTab === 'backup') loadBackup();
  updateTaskPolling();
  showToast('☁️ Iniciando sincronização com Google Drive…');

  try {
    const res = await fetch(API + '/api/backup/sync', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('✅ Backup iniciado em segundo plano');
    } else {
      showToast('❌ ' + (data.message || 'Falha ao iniciar backup'));
      if (!data.message || !data.message.includes('already running')) {
        delete currentTasks[taskKey];
        delete previousTasks[taskKey];
        if (currentTab === 'backup') loadBackup();
      }
      pollTasksOnly();
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
    delete currentTasks[taskKey];
    delete previousTasks[taskKey];
    if (currentTab === 'backup') loadBackup();
    updateTaskPolling();
  }
}

// ── Utilities ──────────────────────────────────────
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function showToast(msg) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.style.cssText = '' +
      'position: fixed; bottom: 24px; right: 24px; z-index: 9999;' +
      'padding: 12px 20px; border-radius: 10px; font-size: 0.82rem;' +
      'background: #1e293b; color: #f1f5f9; border: 1px solid #334155;' +
      'box-shadow: 0 10px 15px rgba(0,0,0,0.4);' +
      'opacity: 0; transition: opacity 0.3s ease; pointer-events: none;';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  setTimeout(function() { toast.style.opacity = '0'; }, 3500);
}

// Keyboard shortcut: Escape closes modal
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeModal();
});

// ══════════════════════════════════════════════════
// Curadoria & Quality Control (QC) Logic
// ══════════════════════════════════════════════════

let currentQCFilter = 'all';
let currentQCConfig = { mode: 'auto', min_score: 7.5, auto_upscale: true };

async function loadQC() {
  const grid = document.getElementById('qc-grid');
  if (!grid) return;

  try {
    const [cfgRes, dataRes] = await Promise.all([
      fetch(API + '/api/qc/config'),
      fetch(API + '/api/qc/images?filter=' + encodeURIComponent(currentQCFilter)),
    ]);

    if (cfgRes.ok) {
      currentQCConfig = await cfgRes.json();
    }

    if (dataRes.ok) {
      const data = await dataRes.json();
      renderQCControls(currentQCConfig, data.stats);
      renderQCCards(data.images, data.stats);
      loadQCPacks();
    }
  } catch (err) {
    console.error('Error loading QC:', err);
    if (grid) grid.innerHTML = '<div class="loading">Erro ao carregar dados de QC.</div>';
  }
}

function renderQCControls(config, stats) {
  const autoBtn = document.getElementById('qc-mode-auto-btn');
  const manualBtn = document.getElementById('qc-mode-manual-btn');
  if (autoBtn && manualBtn) {
    if (config.mode === 'auto') {
      autoBtn.className = 'qc-toggle-btn active';
      manualBtn.className = 'qc-toggle-btn';
    } else {
      manualBtn.className = 'qc-toggle-btn active';
      autoBtn.className = 'qc-toggle-btn';
    }
  }

  const minScoreInput = document.getElementById('qc-min-score');
  if (minScoreInput && document.activeElement !== minScoreInput) {
    minScoreInput.value = config.min_score || 7.5;
  }

  if (stats) {
    const elAll = document.getElementById('qc-count-all');
    const elPending = document.getElementById('qc-count-pending');
    const elApproved = document.getElementById('qc-count-approved');
    const elRejected = document.getElementById('qc-count-rejected');
    const elUpscaled = document.getElementById('qc-count-upscaled');
    const elApprovedBtn = document.getElementById('qc-approved-count');
    const elStat = document.getElementById('qc-stat');

    if (elAll) elAll.textContent = stats.total_staging || 0;
    if (elPending) elPending.textContent = stats.pending || 0;
    if (elApproved) elApproved.textContent = stats.approved || 0;
    if (elRejected) elRejected.textContent = stats.rejected || 0;
    if (elUpscaled) elUpscaled.textContent = stats.upscaled || 0;
    if (elApprovedBtn) elApprovedBtn.textContent = stats.approved || 0;

    if (elStat) {
      elStat.textContent = (stats.total_staging || 0) + ' imagens em staging | ' + (stats.approved || 0) + ' aprovadas | ' + (stats.upscaled || 0) + ' prontas em 8K';
    }

    const btnUpscale = document.getElementById('btn-qc-upscale-all');
    if (btnUpscale) {
      btnUpscale.disabled = (stats.approved || 0) === 0;
    }

    const btnEval = document.getElementById('btn-qc-eval-all');
    if (btnEval) {
      btnEval.disabled = (stats.pending || 0) === 0;
    }
  }
}

async function setQCMode(mode) {
  try {
    const res = await fetch(API + '/api/qc/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode }),
    });
    if (res.ok) {
      currentQCConfig = await res.json();
      loadQC();
    }
  } catch (e) {
    console.error('Error setting QC mode:', e);
  }
}

async function updateQCMinScore(val) {
  const num = parseFloat(val);
  if (isNaN(num) || num < 1 || num > 10) return;
  try {
    await fetch(API + '/api/qc/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ min_score: num }),
    });
    loadQC();
  } catch (e) {
    console.error('Error updating QC min score:', e);
  }
}

function filterQC(status) {
  currentQCFilter = status;
  document.querySelectorAll('#tab-qc .filter-btn').forEach(function(b) {
    b.classList.remove('active');
  });
  const activeBtn = document.getElementById('qc-filter-' + status);
  if (activeBtn) activeBtn.classList.add('active');
  loadQC();
}

async function runQCEvaluate() {
  const btn = document.getElementById('btn-qc-eval-all');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '⚡ Avaliando com Gemini...';
  }
  try {
    const res = await fetch(API + '/api/qc/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    console.log('QC Evaluation completed:', data);
    await Promise.all([loadQC(), loadStatus()]);
  } catch (e) {
    console.error('Error running QC evaluate:', e);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '⚡ Avaliar com Gemini';
    }
  }
}

async function packageQCPacks(autoRun) {
  const btn = autoRun ? document.getElementById('btn-qc-zip-and-run') : document.getElementById('btn-qc-package-packs');
  const originalText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = autoRun ? '⏳ Zipando & Iniciando Conta 2...' : '⏳ Gerando Packs de 10...';
  }

  try {
    const res = await fetch(API + '/api/qc/package-zip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pack_size: 10, only_unprocessed: true, auto_run: autoRun }),
    });
    const data = await res.json();
    if (data.success && data.data) {
      const d = data.data;
      if (d.total_packs > 0) {
        showToast('📦 ' + d.total_images + ' imagens empacotadas em ' + d.total_packs + ' packs de 10!');
        renderPacksInfo(d);
        if (autoRun) {
          showToast('🚀 Conta 2 (SeedVR 8K) disparada com sucesso!');
        }
      } else {
        showToast('⚠️ Nenhuma imagem aprovada pendente para empacotar.');
      }
      await loadQC();
    } else {
      showToast('❌ Erro ao empacotar zips: ' + (data.message || 'Falha'));
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
}

async function triggerConta2Bat() {
  const btn = document.getElementById('btn-qc-run-conta2');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '▶️ Iniciando...';
  }

  try {
    const res = await fetch(API + '/api/qc/run-conta2', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'window', batch_size: 10 }),
    });
    const data = await res.json();
    if (data.success) {
      showToast('🚀 ' + (data.message || 'run_conta2.bat disparado com sucesso!'));
    } else {
      showToast('❌ Erro: ' + (data.message || 'Falha ao executar bat'));
    }
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '▶️ Rodar run_conta2.bat';
    }
  }
}

function renderPacksInfo(info) {
  const banner = document.getElementById('qc-packs-banner');
  const text = document.getElementById('qc-packs-text');
  if (!banner || !text) return;

  if (info && info.total_packs > 0) {
    banner.style.display = 'block';
    const firstCount = (info.packs && info.packs[0]) ? info.packs[0].count : 10;
    const packNames = (info.packs || []).map(function(p) { return p.filename; }).join(', ');
    text.innerHTML = '📦 <strong>' + info.total_images + ' imagens aprovadas</strong> divididas em <strong>' + info.total_packs + ' packs</strong> de até 10 imagens.<br>' +
      '• Pack atual pronto para ingestão no Nó #5: <code>approved_batch.zip</code> (' + firstCount + ' imagens)<br>' +
      '• Lista de packs em <code>data/staging/packs/</code>: ' + packNames;
  } else {
    banner.style.display = 'none';
  }
}

async function loadQCPacks() {
  try {
    const res = await fetch(API + '/api/qc/packs');
    if (res.ok) {
      const data = await res.json();
      renderPacksInfo(data);
    }
  } catch (e) {
    // silent
  }
}

async function runQCUpscale() {
  const btn = document.getElementById('btn-qc-upscale-all');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '🚀 Upscaling para 8K...';
  }
  try {
    const res = await fetch(API + '/api/qc/upscale', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    console.log('QC Upscale completed:', data);
    await Promise.all([loadQC(), loadGallery(), loadStatus()]);
  } catch (e) {
    console.error('Error running QC upscale:', e);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '🚀 Upscale 8K Aprovadas (<span id="qc-approved-count">0</span>)';
    }
  }
}

async function setSingleQCStatus(filename, status) {
  try {
    const res = await fetch(API + '/api/qc/set-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: filename, status: status }),
    });
    if (res.ok) {
      loadQC();
    }
  } catch (e) {
    console.error('Error setting single QC status:', e);
  }
}

async function evalSingleQC(filename) {
  try {
    const res = await fetch(API + '/api/qc/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filenames: [filename], force: true }),
    });
    if (res.ok) {
      loadQC();
    }
  } catch (e) {
    console.error('Error evaluating single QC:', e);
  }
}

async function upscaleSingleQC(filename) {
  try {
    const res = await fetch(API + '/api/qc/upscale', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filenames: [filename] }),
    });
    if (res.ok) {
      await Promise.all([loadQC(), loadGallery(), loadStatus()]);
    }
  } catch (e) {
    console.error('Error upscaling single QC:', e);
  }
}

function openQCPreview(filename) {
  window.open(API + '/api/qc/staging/' + encodeURIComponent(filename), '_blank');
}

function renderQCCards(images, stats) {
  const grid = document.getElementById('qc-grid');
  if (!grid) return;

  if (!images || images.length === 0) {
    grid.innerHTML = '<div class="empty-state" style="grid-column: 1/-1; text-align:center; padding: 40px; color:var(--text-muted);">' +
      '<div style="font-size:32px; margin-bottom:10px;">🔍</div>' +
      '<div>Nenhuma imagem em staging para o filtro <strong>' + esc(currentQCFilter) + '</strong>.</div>' +
      '<div style="font-size:12px; margin-top:6px;">Gere imagens em Fase 3 ou envie imagens brutas para <code>data/staging/images/</code> para curadoria.</div>' +
      '</div>';
    return;
  }

  grid.innerHTML = images.map(function(item) {
    const status = item.status || 'pending';
    let statusClass = 'qc-card-pending';
    let badgeText = '⏳ Pendente';
    let badgeClass = 'qc-badge-pending';

    if (status === 'approved') {
      statusClass = 'qc-card-approved';
      badgeText = '✓ Aprovada';
      badgeClass = 'qc-badge-approved';
    } else if (status === 'rejected') {
      statusClass = 'qc-card-rejected';
      badgeText = '✗ Rejeitada';
      badgeClass = 'qc-badge-rejected';
    }

    let upscaledBadge = '';
    if (item.upscaled) {
      upscaledBadge = '<span class="qc-badge-8k" title="Render 4K salvo em data/final/images (8K)">✨ 8K Pronta</span>';
    }

    let scorePill = '';
    if (item.score !== null && item.score !== undefined) {
      const scoreVal = Number(item.score).toFixed(1);
      let scoreColorClass = 'qc-score-mid';
      if (item.score >= 7.5) scoreColorClass = 'qc-score-high';
      else if (item.score < 6.0) scoreColorClass = 'qc-score-low';
      scorePill = '<span class="qc-score-pill ' + scoreColorClass + '">⭐ ' + scoreVal + '</span>';
    }

    let critiqueBoxHtml = '';
    if (item.critique) {
      const c = item.critique;
      let tagsHtml = '';

      if (c.strengths && c.strengths.length > 0) {
        tagsHtml += c.strengths.slice(0, 2).map(function(s) {
          return '<span class="qc-tag qc-tag-strength">✓ ' + esc(s) + '</span>';
        }).join('');
      }

      if (c.flaws && c.flaws.length > 0) {
        tagsHtml += c.flaws.slice(0, 2).map(function(f) {
          return '<span class="qc-tag qc-tag-flaw">⚠️ ' + esc(f) + '</span>';
        }).join('');
      }

      critiqueBoxHtml = '<div class="qc-critique-box">' +
        (c.summary ? ('<div style="margin-bottom:4px;">' + esc(c.summary) + '</div>') : '') +
        (tagsHtml ? ('<div class="qc-critique-tags">' + tagsHtml + '</div>') : '') +
        '</div>';
    }

    const createdDate = item.created_at ? new Date(item.created_at).toLocaleDateString('pt-BR') : '';

    return '' +
      '<div class="qc-card ' + statusClass + '">' +
        '<div class="qc-card-img-wrap" onclick="openQCPreview(\'' + esc(item.filename) + '\')">' +
          '<span class="qc-badge ' + badgeClass + '">' + badgeText + '</span>' +
          upscaledBadge +
          scorePill +
          '<img src="' + API + '/api/qc/staging/' + encodeURIComponent(item.filename) + '/thumb" alt="' + esc(item.filename) + '" loading="lazy" onerror="this.onerror=null;this.src=\'/static/img/placeholder.png\';">' +
        '</div>' +
        '<div class="qc-card-body">' +
          '<div class="qc-card-header">' +
            '<span class="qc-card-title" title="' + esc(item.filename) + '">' + esc(item.filename) + '</span>' +
            '<span class="qc-card-date">' + createdDate + '</span>' +
          '</div>' +
          critiqueBoxHtml +
          '<div class="qc-card-actions">' +
            '<button class="btn-qc-action btn-qc-approve" onclick="setSingleQCStatus(\'' + esc(item.filename) + '\', \'approved\')" title="Aprovar imagem para upscale 4K">✓ Aprovar</button>' +
            '<button class="btn-qc-action btn-qc-reject" onclick="setSingleQCStatus(\'' + esc(item.filename) + '\', \'rejected\')" title="Rejeitar imagem (não fará upscale)">✗ Rejeitar</button>' +
            '<button class="btn-qc-action btn-qc-eval" onclick="evalSingleQC(\'' + esc(item.filename) + '\')" title="Auditar com Gemini Vision">⚡ IA</button>' +

          '</div>' +
        '</div>' +
      '</div>';
  }).join('');
}


// ══════════════════════════════════════════════════════
// 24/7 Production Daemon & Rolling Weekly Quotas UI
// ══════════════════════════════════════════════════════

async function loadDaemon() {
  const container = document.getElementById('daemon-container');
  if (!container) return;

  try {
    const res = await fetch(API + '/api/daemon/status');
    if (!res.ok) throw new Error('Falha ao carregar status do daemon');
    const data = await res.json();
    renderDaemon(data);
  } catch (err) {
    container.innerHTML = '<div class="card" style="padding:20px; color:#f87171;">Erro ao carregar dados do Daemon: ' + err.message + '</div>';
  }
}

function renderDaemon(data) {
  const container = document.getElementById('daemon-container');
  if (!container) return;

  const isRunning = data.status === 'running';
  const isPaused = data.status === 'paused';

  let statusBadge = '<span class="pill" style="background:#334155; color:#94a3b8; font-size:0.85rem; padding:6px 14px;">⏹️ PARADO</span>';
  if (isRunning) {
    statusBadge = '<span class="pill pill-ok" style="font-size:0.85rem; padding:6px 14px;">🟢 EM PRODUÇÃO 24/7 (ATIVO)</span>';
  } else if (isPaused) {
    statusBadge = '<span class="pill pill-warn" style="font-size:0.85rem; padding:6px 14px;">⏸️ PAUSADO</span>';
  }

  const heartbeatTime = data.last_heartbeat ? new Date(data.last_heartbeat).toLocaleTimeString('pt-BR') : '—';
  const cycles = data.cycles_completed || 0;
  const currentPhase = data.current_phase || 'Aguardando inicialização';
  const currentAction = data.current_action || 'Nenhuma ação no momento';

  const vault = data.vault || {
    total_local_assets: 0,
    pending_distribution: 0,
    fully_distributed: 0,
    gdrive_backed_up: 0,
    purged_from_local_ssd: 0
  };

  const quotas = data.quotas || {};

  // Build Quota Cards HTML
  let quotaCardsHtml = '';
  for (const [key, rep] of Object.entries(quotas)) {
    const isAlamy = key === 'alamy';
    const limit = rep.weekly_limit || 0;
    const used = rep.uploads_last_7_days || 0;
    const available = rep.slots_available || 0;
    const isExhausted = rep.is_quota_exhausted;

    let barColor = '#10b981';
    let percent = 0;
    if (limit > 0) {
      percent = Math.min(100, Math.round((used / limit) * 100));
      if (isExhausted) barColor = '#a855f7';
      else if (percent >= 70) barColor = '#f59e0b';
    }

    let statusHtml = '';
    if (isAlamy || limit === 0) {
      statusHtml = '<span style="color:#ef4444; font-size:0.75rem; font-weight:600;">⛔ BLOQUEADO (Política Anti-IA)</span>';
    } else if (isExhausted) {
      statusHtml = '<span style="color:#c084fc; font-size:0.75rem; font-weight:600;">⏸️ Cota Atingida (' + (rep.countdown_str || 'Aguardando') + ')</span>';
    } else {
      statusHtml = '<span style="color:#34d399; font-size:0.75rem; font-weight:600;">🟢 ' + available + ' vagas disponíveis</span>';
    }

    quotaCardsHtml += `
      <div class="card" style="background:#131b2e; border:1px solid #1e293b; border-radius:10px; padding:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <span style="font-weight:700; font-size:0.9rem; text-transform:uppercase; color:#e2e8f0;">${key}</span>
          ${statusHtml}
        </div>
        <div style="background:#0f172a; border-radius:6px; overflow:hidden; height:10px; margin:10px 0;">
          <div style="width:${percent}%; background:${barColor}; height:100%; transition:width 0.4s ease;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94a3b8;">
          <span>Envios (7D): <strong style="color:#f8fafc;">${used}</strong> / ${limit}</span>
          <span>${percent}%</span>
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    <!-- Top Hero Card -->
    <div class="card" style="background:linear-gradient(135deg, #0d1527 0%, #17223b 100%); border:1px solid #253350; border-radius:12px; padding:22px; margin-bottom:20px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
        <div>
          <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
            <h2 style="font-size:1.25rem; font-weight:700; color:#38bdf8; margin:0;">🤖 Fábrica Autônoma 24/7 (Supervisor Daemon)</h2>
            ${statusBadge}
          </div>
          <p style="color:#94a3b8; font-size:0.85rem; margin:0 0 8px 0;">
            Ciclos de produção contínua com gestão inteligente de cotas semanais e cofre em nuvem.
          </p>
          <div style="display:flex; gap:20px; font-size:0.8rem; color:#cbd5e1; margin-top:12px;">
            <span>📍 Fase: <strong style="color:#38bdf8;">${currentPhase}</strong></span>
            <span>⚡ Ação: <strong style="color:#e2e8f0;">${currentAction}</strong></span>
            <span>🔄 Ciclos: <strong style="color:#34d399;">#${cycles}</strong></span>
            <span>💓 Heartbeat: <strong style="color:#94a3b8;">${heartbeatTime}</strong></span>
          </div>
        </div>

        <!-- Controls -->
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          ${!isRunning ? `
            <button class="btn btn-primary" onclick="triggerStartDaemon('background')" style="display:flex; align-items:center; gap:6px;">
              ▶️ Iniciar 24/7 (Background)
            </button>
            <button class="btn btn-outline" onclick="triggerStartDaemon('window')" style="display:flex; align-items:center; gap:6px;">
              💻 Abrir no Console (run_24_7.bat)
            </button>
          ` : `
            <button class="btn btn-danger" onclick="triggerStopDaemon()" style="display:flex; align-items:center; gap:6px;">
              ⏹️ Parar Daemon 24/7
            </button>
          `}
          <button class="btn btn-secondary" onclick="loadDaemon()" title="Recarregar status">🔄 Atualizar</button>
        </div>
      </div>
    </div>

    <!-- Vault & Cloud Storage Metrics -->
    <h3 style="font-size:1rem; font-weight:700; color:#f8fafc; margin-bottom:12px;">
      🏦 O Cofre & Armazenamento Seguro
    </h3>
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:14px; margin-bottom:24px;">
      <div class="card" style="background:#131b2e; border:1px solid #1e293b; border-radius:10px; padding:14px;">
        <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:4px;">📁 Assets no Disco Local</div>
        <div style="font-size:1.4rem; font-weight:800; color:#38bdf8;">${vault.total_local_assets}</div>
        <div style="font-size:0.7rem; color:#64748b; margin-top:2px;">data/final/images/</div>
      </div>

      <div class="card" style="background:#131b2e; border:1px solid #1e293b; border-radius:10px; padding:14px;">
        <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:4px;">⏳ Engatilhados (Aguardando Cotas)</div>
        <div style="font-size:1.4rem; font-weight:800; color:#fbbf24;">${vault.pending_distribution}</div>
        <div style="font-size:0.7rem; color:#64748b; margin-top:2px;">Prontos para envio futuro</div>
      </div>

      <div class="card" style="background:#131b2e; border:1px solid #1e293b; border-radius:10px; padding:14px;">
        <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:4px;">🎉 100% Distribuídos</div>
        <div style="font-size:1.4rem; font-weight:800; color:#34d399;">${vault.fully_distributed}</div>
        <div style="font-size:0.7rem; color:#64748b; margin-top:2px;">Enviados a todas agências ativas</div>
      </div>

      <div class="card" style="background:#131b2e; border:1px solid #1e293b; border-radius:10px; padding:14px;">
        <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:4px;">☁️ No Cofre (Google Drive)</div>
        <div style="font-size:1.4rem; font-weight:800; color:#818cf8;">${vault.gdrive_backed_up}</div>
        <div style="font-size:0.7rem; color:#64748b; margin-top:2px;">100% seguros na nuvem</div>
      </div>

      <div class="card" style="background:#131b2e; border:1px solid #1e293b; border-radius:10px; padding:14px;">
        <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:4px;">🧹 Liberados do SSD (Auto-Purga)</div>
        <div style="font-size:1.4rem; font-weight:800; color:#ec4899;">${vault.purged_from_local_ssd}</div>
        <div style="font-size:0.7rem; color:#64748b; margin-top:2px;">Espaço em disco poupado</div>
      </div>
    </div>

    <!-- Weekly Quotas (Rolling 7 Days) Grid -->
    <h3 style="font-size:1rem; font-weight:700; color:#f8fafc; margin-bottom:12px;">
      📊 Cotas Semanais por Agência (Janela Deslizante de 7 Dias)
    </h3>
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:14px;">
      ${quotaCardsHtml}
    </div>
  `;
}

async function triggerStartDaemon(mode = 'background') {
  try {
    const res = await fetch(API + '/api/daemon/start?mode=' + encodeURIComponent(mode), {
      method: 'POST'
    });
    const result = await res.json();
    if (result.success) {
      alert('🚀 ' + result.message);
      setTimeout(loadDaemon, 1000);
    } else {
      alert('⚠️ ' + result.message);
    }
  } catch (err) {
    alert('Erro ao iniciar Daemon: ' + err.message);
  }
}

async function triggerStopDaemon() {
  if (!confirm('Deseja realmente parar o Daemon 24/7?')) return;
  try {
    const res = await fetch(API + '/api/daemon/stop', { method: 'POST' });
    const result = await res.json();
    alert('🛑 ' + result.message);
    setTimeout(loadDaemon, 1000);
  } catch (err) {
    alert('Erro ao parar Daemon: ' + err.message);
  }
}
