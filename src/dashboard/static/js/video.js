/**
 * StockCont Cinema & Video Command Center SPA Logic
 * Hardware-accelerated, Apple HIG tactile interactions, auto-sync telemetry.
 */

// ── Global State ─────────────────────────────────────
let videoState = {
  status: null,
  activeTab: 'gallery',
  videos: [],
  filteredVideos: [],
  prompts: [],
  filteredPrompts: [],
  selectedPromptHashes: new Set(),
  i2vImages: [],
  matrix: null,
  tasks: {},
  filterGallery: 'all',
  filterQueue: 'all',
  filterAspect: 'all',
  autoSyncInterval: null,
};

// ── Initialization ───────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initVideoDashboard();
});

function initVideoDashboard() {
  refreshVideoAll();
  videoState.autoSyncInterval = setInterval(refreshVideoAll, 15000);

  // Keyboard shortcut: Escape closes modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeVideoModal();
      closePromptModal();
    }
  });
}

async function refreshVideoAll() {
  const syncBtn = document.getElementById('btn-refresh');
  if (syncBtn) syncBtn.classList.add('spinning');

  try {
    await Promise.all([
      loadVideoStatus(),
      loadRunningTasks(),
    ]);

    // Load active tab data
    if (videoState.activeTab === 'gallery') await loadVideoGallery();
    else if (videoState.activeTab === 'queue') await loadVideoQueue();
    else if (videoState.activeTab === 'i2v') await loadI2VStudio();
    else if (videoState.activeTab === 'matrix') await loadVideoMatrix();
    else if (videoState.activeTab === 'agencies') await loadVideoAgencies();
    else if (videoState.activeTab === 'timeline') await loadVideoTimeline();

    const lastRef = document.getElementById('last-refresh');
    if (lastRef) {
      const now = new Date();
      lastRef.textContent = now.toLocaleTimeString('pt-BR');
    }
  } catch (err) {
    console.error('Error refreshing video dashboard:', err);
  } finally {
    if (syncBtn) {
      setTimeout(() => syncBtn.classList.remove('spinning'), 500);
    }
  }
}

// ── Tab Switching ────────────────────────────────────
function switchVideoTab(tabName) {
  videoState.activeTab = tabName;

  document.querySelectorAll('nav.tabs .tab').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  document.querySelectorAll('.tab-content').forEach((sec) => {
    sec.classList.toggle('active', sec.id === `tab-${tabName}`);
  });

  if (tabName === 'gallery') loadVideoGallery();
  else if (tabName === 'queue') loadVideoQueue();
  else if (tabName === 'i2v') loadI2VStudio();
  else if (tabName === 'matrix') loadVideoMatrix();
  else if (tabName === 'agencies') loadVideoAgencies();
  else if (tabName === 'timeline') loadVideoTimeline();
}

// ── Status & KPIs ────────────────────────────────────
async function loadVideoStatus() {
  try {
    const res = await fetch('/api/video/status');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    videoState.status = data;

    const kpis = data.kpis || {};

    // Update KPI card values
    setElText('kpi-val-trends', kpis.trends ?? 0);
    setElText('kpi-val-prompts', kpis.prompts_total ?? 0);
    setElText('kpi-val-queue', `${kpis.queue_generated ?? 0} / ${kpis.prompts_total ?? 0}`);
    setElText('kpi-val-videos', kpis.videos_total ?? 0);
    setElText('kpi-val-cataloged', `${kpis.videos_cataloged ?? 0} / ${kpis.videos_total ?? 0}`);
    setElText('kpi-val-distributed', kpis.videos_distributed ?? 0);

    // Progress bar for queue
    const qProg = document.getElementById('queue-progress');
    if (qProg) {
      qProg.style.width = `${kpis.queue_percent || 0}%`;
    }

    // Gemini Pill
    const gemPill = document.getElementById('gemini-pill');
    if (gemPill) {
      if (kpis.gemini_configured) {
        gemPill.className = 'pill pill-ok';
        gemPill.title = 'Gemini Vision 4D Cinematography Conectado';
      } else {
        gemPill.className = 'pill pill-warn';
        gemPill.title = 'Configure GEMINI_API_KEY no .env';
      }
    }

    // Render 5 Pipeline Track Nodes
    renderVideoPipelineTrack(data.phases || []);
  } catch (e) {
    console.error('Failed to load video status:', e);
  }
}

function renderVideoPipelineTrack(phases) {
  const container = document.getElementById('video-pipeline-track');
  if (!container) return;

  container.innerHTML = phases.map((p) => {
    let statusClass = 'node-idle';
    let ledClass = 'pulse-led-idle';

    if (p.status === 'ok') {
      statusClass = 'node-ok';
      ledClass = 'pulse-led-ok';
    } else if (p.status === 'warning') {
      statusClass = 'node-warning';
      ledClass = 'pulse-led-warn';
    }

    let actionBtn = '';
    if (p.phase === 1) {
      actionBtn = `<button class="btn btn-xs btn-outline" onclick="triggerRunVideoPhase(1)">Scout</button>`;
    } else if (p.phase === 2) {
      actionBtn = `<button class="btn btn-xs btn-primary" onclick="triggerRunVideoPhase(2)">Sintetizar</button>`;
    } else if (p.phase === 3) {
      actionBtn = `<button class="btn btn-xs btn-warning" onclick="triggerRunVideoPhase(3)" title="Gerar e Upscale 4K no RunningHub (Img #164, Prompt #17, Vídeo #157)">Gerar 4K</button>`;
    } else if (p.phase === 4) {
      actionBtn = `<button class="btn btn-xs btn-warning" onclick="triggerRunVideoPhase(4)">Catalogar</button>`;
    } else if (p.phase === 5) {
      actionBtn = `<button class="btn btn-xs btn-success" onclick="triggerRunVideoPhase(5)">Distribuir</button>`;
    }

    return `
      <div class="pipeline-node ${statusClass}">
        <div class="node-header">
          <span class="pulse-led ${ledClass}"></span>
          <span class="node-phase mono">FASE ${p.phase}</span>
        </div>
        <div class="node-name">${p.name}</div>
        <div class="node-detail meta-text">${p.detail || p.subtitle || ''}</div>
        <div class="node-action" style="margin-top:8px;">${actionBtn}</div>
      </div>
    `;
  }).join('');
}

// ── Tab 1: Video Gallery & Cinema Player ─────────────
async function loadVideoGallery() {
  const grid = document.getElementById('video-grid');
  const stat = document.getElementById('video-gallery-stat');
  if (!grid) return;

  try {
    const res = await fetch('/api/video/items');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    videoState.videos = data.videos || [];

    applyVideoFilter();
  } catch (err) {
    grid.innerHTML = `<div class="loading" style="color:var(--color-system-red);">Erro ao carregar vídeos: ${err.message}</div>`;
  }
}

function filterVideos(mode) {
  videoState.filterGallery = mode;
  document.querySelectorAll('#tab-gallery .filter-btn').forEach((b) => {
    b.classList.toggle('active', b.textContent.toLowerCase().includes(mode.toLowerCase()) || (mode === 'all' && b.textContent === 'Todos'));
  });
  applyVideoFilter();
}

function applyVideoFilter() {
  const grid = document.getElementById('video-grid');
  const stat = document.getElementById('video-gallery-stat');
  if (!grid) return;

  let list = videoState.videos;
  if (videoState.filterGallery === 'cataloged') {
    list = list.filter((v) => v.is_cataloged);
  } else if (videoState.filterGallery === 'uncataloged') {
    list = list.filter((v) => !v.is_cataloged);
  }

  videoState.filteredVideos = list;
  if (stat) {
    stat.textContent = `${list.length} de ${videoState.videos.length} vídeo(s)`;
  }

  if (list.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 40px; text-align: center; background: rgba(255,255,255,0.02); border-radius: 16px; border: 1px dashed rgba(255,255,255,0.15);">
        <p style="color: var(--label-secondary); font-size: 0.95rem; margin-bottom: 12px;">Nenhum vídeo renderizado encontrado em <code>data/final/videos/</code>.</p>
        <button class="btn btn-sm btn-primary" onclick="switchVideoTab('i2v')">
          <span>Ir para o Estúdio I2V e Sintetizar de Imagens 8K</span>
        </button>
      </div>
    `;
    return;
  }

  grid.innerHTML = list.map((v) => {
    const isCat = v.is_cataloged;
    const catBadge = isCat
      ? `<span class="tech-badge tech-badge-ok">Catalogado</span>`
      : `<span class="tech-badge tech-badge-warn">Pendente CSV</span>`;

    const posterSrc = v.poster_url || `/api/video/poster/${v.filename}`;

    return `
      <div class="video-card" onclick="openCinemaVideoModal('${v.filename}')">
        <div class="video-card-thumb-wrap">
          <img class="video-card-thumb" src="${posterSrc}" alt="${v.title}" onerror="this.src='/static/favicon.svg'; this.style.padding='40px';" loading="lazy">
          <div class="video-play-overlay">
            <div class="video-play-btn">
              <svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor">
                <polygon points="5,3 13,8 5,13" />
              </svg>
            </div>
          </div>
          <div class="video-badges-floating">
            <span class="tech-badge tech-badge-idle">4K UHD</span>
            ${catBadge}
          </div>
          <div class="video-duration-badge mono">00:08</div>
        </div>
        <div class="video-card-body">
          <div class="video-card-title" title="${v.title}">${v.title}</div>
          <div class="video-card-meta-row mono">
            <span>${v.size_mb} MB</span>
            <span>MP4 Rec.709</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ── Interactive Cinema Modal & Player ────────────────
async function openCinemaVideoModal(filename) {
  const modal = document.getElementById('video-modal-overlay');
  const player = document.getElementById('cinema-video-player');
  const source = document.getElementById('cinema-video-source');
  const titleEl = document.getElementById('cinema-modal-title');
  const fnameEl = document.getElementById('cinema-modal-filename');
  const techGrid = document.getElementById('cinema-tech-grid');
  const metaContainer = document.getElementById('cinema-modal-meta');

  if (!modal || !player || !source) return;

  titleEl.textContent = 'Carregando detalhes do vídeo…';
  fnameEl.textContent = filename;
  techGrid.innerHTML = '<div class="loading">Inspecionando propriedades com ffprobe…</div>';
  metaContainer.innerHTML = '';

  // Setup streaming source
  source.src = `/api/video/stream/${filename}`;
  player.load();
  player.play().catch(() => {});

  modal.classList.add('active');

  try {
    const res = await fetch(`/api/video/meta/${filename}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const meta = await res.json();

    const tech = meta.technical || {};
    titleEl.textContent = meta.adobe_csv?.Title || meta.pond5_csv?.Title || filename.replace(/_/g, ' ').replace(/\.[^/.]+$/, '');

    techGrid.innerHTML = `
      <div class="video-tech-item">
        <span class="video-tech-label">Resolução</span>
        <span class="video-tech-val">${tech.width || 3840}x${tech.height || 2160}</span>
      </div>
      <div class="video-tech-item">
        <span class="video-tech-label">Aspect Ratio</span>
        <span class="video-tech-val">${tech.aspect_ratio || '16:9'}</span>
      </div>
      <div class="video-tech-item">
        <span class="video-tech-label">Duração</span>
        <span class="video-tech-val">${tech.duration_seconds || '8.0'}s</span>
      </div>
      <div class="video-tech-item">
        <span class="video-tech-label">Taxa de Quadros</span>
        <span class="video-tech-val">${tech.fps || '24.0'} fps</span>
      </div>
      <div class="video-tech-item">
        <span class="video-tech-label">Áudio de IA</span>
        <span class="video-tech-val" style="color:${tech.has_audio ? 'var(--color-system-amber)' : 'var(--color-system-green)'};">
          ${tech.has_audio ? 'Com Áudio (Requer Mudo)' : 'Mudo Limpo (-an) ✓'}
        </span>
      </div>
      <div class="video-tech-item">
        <span class="video-tech-label">Codec / Container</span>
        <span class="video-tech-val">${tech.video_codec || 'h264'} (Rec.709)</span>
      </div>
    `;

    const isAdobe = Boolean(meta.adobe_csv?.Title);
    const isPond5 = Boolean(meta.pond5_csv?.Title);

    metaContainer.innerHTML = `
      <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:14px; margin-top:8px;">
        <div style="font-size:0.75rem; text-transform:uppercase; color:var(--label-secondary); margin-bottom:4px; font-weight:600;">Descrição Comercial de IA</div>
        <p style="font-size:0.86rem; color:#e2e8f0; line-height:1.4; margin-bottom:12px;">
          ${meta.adobe_csv?.Title || meta.pond5_csv?.Description || 'Generative AI footage. Cinematic 4K commercial b-roll scene.'}
        </p>

        <div style="font-size:0.75rem; text-transform:uppercase; color:var(--label-secondary); margin-bottom:6px; font-weight:600;">Tags & Palavras-chave</div>
        <div style="display:flex; flex-wrap:wrap; gap:4px; max-height:80px; overflow-y:auto;">
          ${(meta.adobe_csv?.Keywords || 'generative ai, ai generated, footage, 4k, cinematic, b-roll, commercial')
            .split(',')
            .map((k) => `<span class="pill pill-idle" style="font-size:0.68rem; padding:2px 8px;">${k.trim()}</span>`)
            .join('')}
        </div>

        <div style="margin-top:14px; display:flex; gap:12px; align-items:center;">
          <span class="tech-badge ${isAdobe ? 'tech-badge-ok' : 'tech-badge-warn'}">Adobe Stock Video: ${isAdobe ? 'Registrado ✓' : 'Pendente'}</span>
          <span class="tech-badge ${isPond5 ? 'tech-badge-ok' : 'tech-badge-warn'}">Pond5 Footage: ${isPond5 ? 'Registrado ✓' : 'Pendente'}</span>
        </div>
      </div>
    `;
  } catch (err) {
    techGrid.innerHTML = `<div style="color:var(--color-system-red); font-size:0.8rem;">Falha ao obter metadados: ${err.message}</div>`;
  }
}

function closeVideoModal() {
  const modal = document.getElementById('video-modal-overlay');
  const player = document.getElementById('cinema-video-player');
  if (player) {
    player.pause();
    player.src = '';
  }
  if (modal) modal.classList.remove('active');
}

// ── Tab 2: Fila de Prompts 4D ────────────────────────
async function loadVideoQueue() {
  const tbody = document.getElementById('video-queue-tbody');
  const stat = document.getElementById('video-queue-stat');
  if (!tbody) return;

  try {
    const res = await fetch('/api/video/prompts?per_page=100');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    videoState.prompts = data.items || [];

    applyVideoQueueFilter();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="loading" style="color:var(--color-system-red);">Erro: ${err.message}</td></tr>`;
  }
}

function filterVideoQueue(filter) {
  videoState.filterQueue = filter;
  document.querySelectorAll('#tab-queue .filter-btn').forEach((b) => {
    b.classList.toggle('active', b.textContent.toLowerCase().includes(filter.toLowerCase()) || (filter === 'all' && b.textContent === 'Todos'));
  });
  applyVideoQueueFilter();
}

function applyVideoQueueFilter() {
  const tbody = document.getElementById('video-queue-tbody');
  const stat = document.getElementById('video-queue-stat');
  if (!tbody) return;

  let list = videoState.prompts;
  if (videoState.filterQueue === 'pending') {
    list = list.filter((p) => p.status === 'pending');
  } else if (videoState.filterQueue === 'generated') {
    list = list.filter((p) => p.status === 'generated');
  } else if (videoState.filterQueue === '16:9') {
    list = list.filter((p) => p.aspect_ratio === '16:9');
  } else if (videoState.filterQueue === '9:16') {
    list = list.filter((p) => p.aspect_ratio === '9:16');
  }

  videoState.filteredPrompts = list;
  if (stat) {
    stat.textContent = `${list.length} de ${videoState.prompts.length} prompt(s)`;
  }

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--label-secondary);">Nenhum prompt de vídeo encontrado com o filtro atual.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map((p) => {
    const isChecked = videoState.selectedPromptHashes.has(p.prompt_hash);
    const statusBadge = p.status === 'generated'
      ? `<span class="tech-badge tech-badge-ok">Gerado</span>`
      : `<span class="tech-badge tech-badge-warn">Pendente</span>`;

    const aspectBadge = p.aspect_ratio === '9:16'
      ? `<span class="pill pill-idle" style="color:#AF52DE;">9:16 Vertical</span>`
      : `<span class="pill pill-idle" style="color:#007AFF;">16:9 Wide</span>`;

    return `
      <tr>
        <td style="text-align:center;">
          <input type="checkbox" class="prompt-select-checkbox" data-hash="${p.prompt_hash}" ${isChecked ? 'checked' : ''} onchange="togglePromptSelect('${p.prompt_hash}', this.checked)">
        </td>
        <td class="mono" style="font-size:0.75rem; color:var(--color-system-cyan);">${p.prompt_hash}</td>
        <td>
          <div style="font-weight:600; color:#ffffff; font-size:0.84rem;">${p.concept || p.source_title || 'Cinematic Motion'}</div>
          <div class="meta-text" style="font-size:0.74rem; display:-webkit-box; -webkit-line-clamp:1; -webkit-box-orient:vertical; overflow:hidden;">${p.prompt_text}</div>
        </td>
        <td>${aspectBadge}</td>
        <td>
          <div style="font-size:0.76rem; color:#e2e8f0;">${p.camera_motion || 'Smooth Dolly-in'}</div>
          <div class="meta-text mono" style="font-size:0.68rem;">Copy: ${p.copy_space_zone || 'Clean 35%'}</div>
        </td>
        <td>${statusBadge}</td>
        <td style="text-align:center;">
          <button class="btn btn-xs btn-outline" onclick="openPromptDetail('${p.prompt_hash}')" title="Ver prompt completo de 500-800 palavras">Ver</button>
        </td>
      </tr>
    `;
  }).join('');

  updatePromptActionButtons();
}

function togglePromptSelect(hash, checked) {
  if (checked) videoState.selectedPromptHashes.add(hash);
  else videoState.selectedPromptHashes.delete(hash);
  updatePromptActionButtons();
}

function toggleSelectAllVideoPrompts(checked) {
  videoState.filteredPrompts.forEach((p) => {
    if (checked) videoState.selectedPromptHashes.add(p.prompt_hash);
    else videoState.selectedPromptHashes.delete(p.prompt_hash);
  });
  applyVideoQueueFilter();
}

function updatePromptActionButtons() {
  const count = videoState.selectedPromptHashes.size;
  const countEl = document.getElementById('video-selected-count');
  const btnGen = document.getElementById('btn-video-mark-gen');
  const btnPend = document.getElementById('btn-video-mark-pend');

  if (countEl) countEl.textContent = count;
  if (btnGen) btnGen.disabled = count === 0;
  if (btnPend) btnPend.disabled = count === 0;
}

async function markSelectedVideoGenerated() {
  const hashes = Array.from(videoState.selectedPromptHashes);
  if (hashes.length === 0) return;

  try {
    const res = await fetch('/api/video/prompts/mark-generated', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hashes }),
    });
    if (res.ok) {
      videoState.selectedPromptHashes.clear();
      await loadVideoQueue();
      await loadVideoStatus();
    }
  } catch (e) {
    alert('Erro ao marcar prompts: ' + e.message);
  }
}

async function markSelectedVideoPending() {
  const hashes = Array.from(videoState.selectedPromptHashes);
  if (hashes.length === 0) return;

  try {
    const res = await fetch('/api/video/prompts/mark-pending', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hashes }),
    });
    if (res.ok) {
      videoState.selectedPromptHashes.clear();
      await loadVideoQueue();
      await loadVideoStatus();
    }
  } catch (e) {
    alert('Erro ao reverter prompts: ' + e.message);
  }
}

function openPromptDetail(hash) {
  const prompt = videoState.prompts.find((p) => p.prompt_hash === hash);
  if (!prompt) return;

  const modal = document.getElementById('prompt-modal-overlay');
  const conceptEl = document.getElementById('prompt-modal-concept');
  const textEl = document.getElementById('prompt-modal-text');
  const badgesEl = document.getElementById('prompt-modal-badges');

  if (conceptEl) conceptEl.textContent = prompt.concept || prompt.source_title;
  if (textEl) textEl.value = prompt.prompt_text;
  if (badgesEl) {
    badgesEl.innerHTML = `
      <span class="pill pill-ok mono">${prompt.aspect_ratio}</span>
      <span class="pill pill-idle mono">${prompt.target_duration_sec}s @ ${prompt.target_fps}fps</span>
      <span class="pill pill-idle mono">${prompt.word_count} palavras</span>
      <span class="pill pill-idle">${prompt.camera_motion}</span>
    `;
  }

  if (modal) modal.classList.add('active');
}

function closePromptModal() {
  const modal = document.getElementById('prompt-modal-overlay');
  if (modal) modal.classList.remove('active');
}

function copyPromptTextFromModal() {
  const textEl = document.getElementById('prompt-modal-text');
  if (textEl) {
    navigator.clipboard.writeText(textEl.value);
    alert('Prompt copiado para a área de transferência!');
  }
}

// ── Tab 3: Estúdio I2V (Imagens 8K ➔ Vídeo) ──────────
async function loadI2VStudio() {
  const grid = document.getElementById('i2v-grid');
  const stat = document.getElementById('i2v-stat');
  if (!grid) return;

  try {
    const res = await fetch('/api/video/reference-images');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const images = await res.json();
    videoState.i2vImages = images || [];

    if (stat) stat.textContent = `${images.length} imagem(ns) 8K disponíveis`;

    if (images.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: var(--label-secondary);">
          Nenhuma imagem 8K encontrada em <code>data/final/images/</code>. Execute a produção de imagens primeiro.
        </div>
      `;
      return;
    }

    grid.innerHTML = images.map((img) => {
      const hasPrompts = img.has_video_prompts;
      const statusBadge = hasPrompts
        ? `<span class="tech-badge tech-badge-ok">4 Prompts 4D Criados ✓</span>`
        : `<span class="tech-badge tech-badge-idle">Sem Vídeo Sintetizado</span>`;

      return `
        <div class="i2v-card">
          <div class="i2v-thumb-wrap">
            <img class="i2v-thumb" src="/api/images/${img.filename}/thumb" alt="${img.title}" loading="lazy">
          </div>
          <div class="i2v-card-body">
            <div class="i2v-card-title" title="${img.title}">${img.title}</div>
            <div>${statusBadge}</div>
            <button class="btn btn-sm ${hasPrompts ? 'btn-outline' : 'btn-primary'}" onclick="triggerI2VSynthesis('${img.stem}', this)" style="margin-top:auto;">
              <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.8">
                <polygon points="6,3 12,8 6,13" fill="currentColor" stroke="none" />
              </svg>
              <span>${hasPrompts ? 'Resintetizar Prompts 4D' : 'Sintetizar Prompts 4D'}</span>
            </button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    grid.innerHTML = `<div class="loading" style="color:var(--color-system-red);">Erro ao carregar estúdio I2V: ${err.message}</div>`;
  }
}

async function triggerI2VSynthesis(imageStem, btnElement) {
  if (btnElement) {
    btnElement.disabled = true;
    btnElement.innerHTML = `<span>Sintetizando via Gemini…</span>`;
  }

  try {
    const res = await fetch('/api/video/director/from-image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_stem: imageStem }),
    });
    const data = await res.json();
    if (data.success) {
      alert(`Sintetizador 4D iniciado para: ${imageStem}!`);
      switchVideoTab('timeline');
    } else {
      alert(`Falha: ${data.message}`);
    }
  } catch (err) {
    alert(`Erro na requisição: ${err.message}`);
  } finally {
    if (btnElement) btnElement.disabled = false;
  }
}

// ── Tab 4: Matriz de Distribuição ────────────────────
async function loadVideoMatrix() {
  const thead = document.getElementById('video-matrix-thead');
  const tbody = document.getElementById('video-matrix-tbody');
  const stat = document.getElementById('video-matrix-stat');
  if (!thead || !tbody) return;

  try {
    const res = await fetch('/api/video/matrix');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    videoState.matrix = data;

    const agencies = data.agencies || [];
    const rows = data.rows || [];

    if (stat) stat.textContent = `${rows.length} vídeo(s) monitorados`;

    // Headers
    thead.innerHTML = `
      <tr>
        <th style="min-width:240px;">Vídeo Asset (MP4/MOV)</th>
        <th style="width:90px;">Tamanho</th>
        <th style="width:110px;">Metadados</th>
        ${agencies.map((a) => `<th style="text-align:center; min-width:120px;">${a.name}</th>`).join('')}
      </tr>
    `;

    if (rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="${3 + agencies.length}" style="text-align:center; padding:30px; color:var(--label-secondary);">Nenhum vídeo disponível na matriz.</td></tr>`;
      return;
    }

    // Rows
    tbody.innerHTML = rows.map((r) => {
      const catBadge = r.is_cataloged
        ? `<span class="tech-badge tech-badge-ok">Catalogado</span>`
        : `<span class="tech-badge tech-badge-warn">Pendente</span>`;

      const agencyCols = agencies.map((a) => {
        const agKey = a.key;
        const isUp = r.agencies?.[agKey]?.uploaded;
        return `
          <td style="text-align:center;">
            <input type="checkbox" class="prompt-select-checkbox" ${isUp ? 'checked' : ''} onchange="toggleVideoMatrixCell('${r.filename}', '${agKey}', this.checked)">
          </td>
        `;
      }).join('');

      return `
        <tr>
          <td>
            <div style="font-weight:600; color:#ffffff; font-size:0.82rem;">${r.title}</div>
            <div class="mono meta-text" style="font-size:0.72rem;">${r.filename}</div>
          </td>
          <td class="mono" style="font-size:0.78rem;">${r.size_mb} MB</td>
          <td>${catBadge}</td>
          ${agencyCols}
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading" style="color:var(--color-system-red);">Erro: ${err.message}</td></tr>`;
  }
}

async function toggleVideoMatrixCell(filename, agency, uploaded) {
  try {
    await fetch('/api/video/matrix/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename, agency, uploaded }),
    });
    await loadVideoStatus();
  } catch (e) {
    console.error('Failed to toggle matrix cell:', e);
  }
}

// ── Tab 5: Agências de Vídeo ─────────────────────────
async function loadVideoAgencies() {
  const tbody = document.getElementById('video-agencies-tbody');
  if (!tbody) return;

  const agencies = videoState.status?.agencies || [];
  if (agencies.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="loading">Carregando status dos integradores…</td></tr>`;
    return;
  }

  tbody.innerHTML = agencies.map((a) => {
    const isConfig = a.configured;
    const authBadge = a.allowed
      ? (isConfig ? `<span class="tech-badge tech-badge-ok">Configurado (OK)</span>` : `<span class="tech-badge tech-badge-warn">Credenciais Pendentes</span>`)
      : `<span class="tech-badge tech-badge-error">Bloqueio Anti-Ban</span>`;

    const lastUp = a.last_upload ? new Date(a.last_upload).toLocaleDateString('pt-BR') : '—';

    return `
      <tr>
        <td style="font-weight:600; color:#ffffff;">${a.name}</td>
        <td class="mono">${a.protocol}</td>
        <td>${authBadge}</td>
        <td class="mono" style="font-weight:700; color:var(--color-system-cyan);">${a.uploads || 0}</td>
        <td class="mono">${lastUp}</td>
        <td style="font-size:0.78rem; color:${a.allowed ? 'var(--label-secondary)' : 'var(--color-system-red)'}; font-weight:${a.allowed ? '400' : '600'};">
          ${a.ai_policy}
        </td>
        <td>
          <button class="btn btn-xs ${a.allowed && isConfig ? 'btn-success' : 'btn-outline'}" ${!a.allowed || !isConfig ? 'disabled' : ''} onclick="triggerRunVideoPhase(5, '${a.key}')">
            Despachar
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

// ── Tab 6: Timeline & Task Runner ────────────────────
async function loadRunningTasks() {
  try {
    const res = await fetch('/api/tasks');
    if (res.ok) {
      videoState.tasks = await res.json();
    }
  } catch (e) {
    console.error('Failed to load tasks:', e);
  }
}

async function loadVideoTimeline() {
  const feed = document.getElementById('video-timeline-feed');
  if (!feed) return;

  await loadRunningTasks();
  const tasks = Object.values(videoState.tasks || {});

  if (tasks.length === 0) {
    feed.innerHTML = `
      <div style="padding: 30px; text-align: center; color: var(--label-secondary);">
        Nenhuma tarefa em execução no momento. Use os botões das fases acima para disparar processos.
      </div>
    `;
    return;
  }

  feed.innerHTML = tasks.map((t) => {
    const isRunning = t.status === 'running';
    const statusBadge = isRunning
      ? `<span class="tech-badge tech-badge-warn">Em Execução…</span>`
      : (t.returncode === 0 ? `<span class="tech-badge tech-badge-ok">Concluído</span>` : `<span class="tech-badge tech-badge-error">Falhou</span>`);

    return `
      <div style="background: rgba(15,23,42,0.65); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 14px 18px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span class="mono" style="font-weight: 700; color: #38bdf8;">${t.task_id}</span>
          ${statusBadge}
        </div>
        <div class="mono" style="font-size: 0.78rem; color: #e2e8f0; background: rgba(0,0,0,0.5); padding: 8px 12px; border-radius: 6px; max-height: 120px; overflow-y: auto;">
          ${(t.logs || []).slice(-8).map((l) => `<div>${l}</div>`).join('') || t.last_log || 'Aguardando logs…'}
        </div>
      </div>
    `;
  }).join('');
}

// ── Video Phase Execution ────────────────────────────
async function triggerRunVideoPhase(phase, platform) {
  try {
    let url = `/api/video/run-phase/${phase}`;
    const params = [];
    if (platform) params.push(`platform=${encodeURIComponent(platform)}`);
    if (phase === 3) {
      const modeEl = document.getElementById('video-exec-mode');
      if (modeEl && modeEl.value) {
        params.push(`execute_mode=${encodeURIComponent(modeEl.value)}`);
      }
    }
    if (params.length > 0) {
      url += '?' + params.join('&');
    }

    const res = await fetch(url, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      alert(`Fase ${phase} de Vídeo iniciada com sucesso!`);
      switchVideoTab('timeline');
    } else {
      alert(`Aviso: ${data.message}`);
    }
  } catch (err) {
    alert(`Erro ao iniciar fase: ${err.message}`);
  }
}

// ── Utility Helpers ──────────────────────────────────
function setElText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}
