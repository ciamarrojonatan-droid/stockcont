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
    } else if (currentTab === 'backup') {
      loadBackup();
    } else if (currentTab === 'seasonal') {
      loadSeasonal();
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
    case 'agencies': return loadAgencies();
    case 'timeline': return loadTimeline();
    case 'backup': return loadBackup();
    case 'seasonal': return loadSeasonal();
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
    const title = img.title || img.filename;
    return '' +
      '<div class="gallery-item" onclick="openImageModal(\'' + esc(img.filename) + '\')">' +
        '<img src="/api/images/' + encodeURIComponent(img.filename) + '/thumb" alt="' + esc(title) + '" loading="lazy">' +
        badge +
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

    let actionBtn = '<span style="color:var(--text-muted);font-size:0.7rem;">Concluído</span>';
    if (isPending) {
      actionBtn = '<button class="btn btn-sm btn-success" style="padding:2px 8px;font-size:0.68rem;" data-hash="' + esc(hash) + '" onclick="markSinglePromptGenerated(this.dataset.hash)" title="Marcar este prompt individual como gerado">✓ Gerado</button>';
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
      if (currentQueueFilter === 'all' || currentQueueFilter === 'pending') {
        if (p.status === 'pending') {
          selectedPromptHashes.add(hash);
        }
      } else {
        selectedPromptHashes.add(hash);
      }
    });
    if (selectedPromptHashes.size === 0 && currentQueueItems.length > 0) {
      currentQueueItems.forEach(function(p) {
        selectedPromptHashes.add(p.full_hash || p.prompt_hash);
      });
    }
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
  const countEl = document.getElementById('selected-count');
  if (countEl) countEl.textContent = selectedPromptHashes.size;

  const btnMark = document.getElementById('btn-mark-selected');
  if (btnMark) {
    btnMark.disabled = selectedPromptHashes.size === 0;
  }

  const selectAllCb = document.getElementById('select-all-prompts');
  if (selectAllCb) {
    const visiblePending = currentQueueItems.filter(function(i) { return i.status === 'pending'; });
    const checkTarget = visiblePending.length > 0 ? visiblePending : currentQueueItems;
    if (checkTarget.length > 0 && checkTarget.every(function(p) { return selectedPromptHashes.has(p.full_hash || p.prompt_hash); })) {
      selectAllCb.checked = true;
      selectAllCb.indeterminate = false;
    } else if (selectedPromptHashes.size > 0) {
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

function filterQueue(f) {
  currentQueueFilter = f;
  document.querySelectorAll('#tab-queue .filter-btn').forEach(function(b) { b.classList.remove('active'); });
  if (event && event.target) event.target.classList.add('active');
  loadQueue();
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
    return '' +
      '<tr>' +
        '<td><strong>' + esc(a.name) + '</strong></td>' +
        '<td class="mono">' + a.protocol + '</td>' +
        '<td>' + statusChip + '</td>' +
        '<td class="mono">' + a.uploads + '</td>' +
        '<td class="mono">' + lastUpload + '</td>' +
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