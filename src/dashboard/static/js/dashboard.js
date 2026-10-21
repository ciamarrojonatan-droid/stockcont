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

// ── Load Status (KPIs + Pipeline) ──────────────────
async function loadStatus() {
  const res = await fetch(API + '/api/status');
  const data = await res.json();
  renderKPIs(data.kpis);
  renderPipeline(data.phases);

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

function renderPipeline(phases) {
  const track = document.getElementById('pipeline-track');
  track.innerHTML = phases.map(function(p) {
    const badgeClass = 'badge-' + p.status;
    const countText = p.total ? (p.count + '/' + p.total) : p.count;
    let progressHtml = '';
    if (p.total && p.total > 0) {
      const pct = Math.round((p.count / p.total) * 100);
      progressHtml = '<div class="phase-progress"><div class="phase-progress-fill" style="width:' + pct + '%"></div></div>';
    }
    return '' +
      '<div class="phase-node">' +
        '<div class="phase-icon">' + p.icon + '</div>' +
        '<div class="phase-name">' + p.name + '</div>' +
        '<div class="phase-count">' + countText + '</div>' +
        '<div class="phase-detail">' + p.detail + '</div>' +
        progressHtml +
        '<span class="phase-badge ' + badgeClass + '"></span>' +
        '<div class="phase-actions">' +
          '<button class="btn btn-run" onclick="runPhase(' + p.phase + ')">▶ Run</button>' +
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
async function loadQueue() {
  const res = await fetch(API + '/api/prompts?filter=' + currentQueueFilter + '&per_page=200');
  const data = await res.json();

  const gen = data.items.filter(function(i) { return i.status === 'generated'; }).length;
  const pend = data.items.filter(function(i) { return i.status === 'pending'; }).length;
  document.getElementById('queue-stat').textContent =
    gen + ' gerados | ' + pend + ' pendentes | ' + data.total + ' total';

  const tbody = document.getElementById('queue-tbody');
  if (!data.items || data.items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="loading">Nenhum prompt encontrado</td></tr>';
    return;
  }

  tbody.innerHTML = data.items.map(function(p) {
    const chipClass = p.status === 'generated' ? 'chip-generated' : 'chip-pending';
    const statusIcon = p.status === 'generated' ? '✅' : '⏳';
    const date = p.generated_at ? new Date(p.generated_at).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'short'}) : '—';
    return '' +
      '<tr>' +
        '<td class="mono">' + esc(p.prompt_hash) + '</td>' +
        '<td>' + esc(p.concept || '—') + '</td>' +
        '<td class="mono">' + esc(p.source_id || '—') + '</td>' +
        '<td><span class="status-chip ' + chipClass + '">' + statusIcon + ' ' + p.status + '</span></td>' +
        '<td class="mono">' + date + '</td>' +
      '</tr>';
  }).join('');
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

  const tbody = document.getElementById('agencies-tbody');
  tbody.innerHTML = agencies.map(function(a) {
    const statusChip = a.configured
      ? '<span class="status-chip chip-configured">🟢 Configurado</span>'
      : '<span class="status-chip chip-not-configured">⚪ Não configurado</span>';
    const lastUpload = a.last_upload ? new Date(a.last_upload).toLocaleString('pt-BR', {dateStyle:'short',timeStyle:'short'}) : '—';
    const actions = a.configured
      ? '<button class="btn btn-run" onclick="runUpload(\'' + a.key + '\')">Enviar</button>'
      : '<span style="color:var(--text-muted);font-size:0.7rem">Configure no .env</span>';
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

  const card = document.getElementById('backup-card');
  const statusText = b.configured ? ('🟢 Ativo (' + (b.mode || 'unknown') + ')') : '🔴 Não configurado';
  const lastSyncText = b.last_sync ? new Date(b.last_sync).toLocaleString('pt-BR') : '—';
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
      '<button class="btn btn-run ' + (b.configured ? '' : 'btn-disabled') + '" onclick="runBackupSync()">' +
        '☁️ Sync Now' +
      '</button>' +
    '</div>';
}

// ── Seasonal Radar ─────────────────────────────────
async function loadSeasonal() {
  const res = await fetch(API + '/api/seasonal');
  const data = await res.json();

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
        '<button class="seasonal-btn-mine" onclick="mineNiche(\'' + esc(n.query) + '\')">' +
          '🚀 Minerar este Nicho (Fase 1)' +
        '</button>' +
      '</div>';
  }).join('');
}

async function mineNiche(query) {
  if (!confirm('Iniciar mineração da Fase 1 para o nicho:\n"' + query + '"?')) return;
  try {
    const res = await fetch(API + '/api/run-phase/1?query=' + encodeURIComponent(query) + '&mode=search', { method: 'POST' });
    const data = await res.json();
    showToast(data.success ? ('✅ Mineração iniciada para: ' + query) : ('❌ ' + data.message));
    setTimeout(refreshAll, 2000);
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

// ── Actions ────────────────────────────────────────
async function runPhase(n) {
  if (!confirm('Iniciar Fase ' + n + '?')) return;
  try {
    const res = await fetch(API + '/api/run-phase/' + n, { method: 'POST' });
    const data = await res.json();
    showToast(data.success ? ('✅ ' + data.message) : ('❌ ' + data.message));
    setTimeout(refreshAll, 2000);
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

async function runUpload(agency) {
  if (!confirm('Enviar assets para ' + agency + '?')) return;
  showToast('🚀 Upload para ' + agency + ' iniciado… (via Phase 5)');
  try {
    const res = await fetch(API + '/api/run-phase/5', { method: 'POST' });
    const data = await res.json();
    showToast(data.success ? ('✅ ' + data.message) : ('❌ ' + data.message));
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
  }
}

async function runBackupSync() {
  try {
    const res = await fetch(API + '/api/backup/sync', { method: 'POST' });
    const data = await res.json();
    showToast(data.success ? '✅ Backup iniciado' : ('❌ ' + data.message));
    setTimeout(loadBackup, 3000);
  } catch (e) {
    showToast('❌ Erro: ' + e.message);
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
