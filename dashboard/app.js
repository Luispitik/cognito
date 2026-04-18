// =============================================================================
// Cognitio Dashboard — app.js
// =============================================================================
// Fetch data.json y renderiza KPIs, charts, tablas.
// Sin frameworks: vanilla JS + Tailwind CDN + Chart.js CDN.
// =============================================================================

const PALETTE = {
  primary: '#0ea5e9',
  secondary: '#8b5cf6',
  ok: '#10b981',
  warn: '#f59e0b',
  err: '#ef4444',
  muted: '#94a3b8',
  phases: {
    discovery: '#0ea5e9',
    planning: '#ec4899',
    execution: '#f59e0b',
    review: '#8b5cf6',
    shipping: '#10b981',
    unknown: '#94a3b8',
  },
};

const charts = {};

// HTML-escape helper. All dynamic values interpolated into innerHTML
// templates MUST go through this to avoid DOM-based XSS from a poisoned
// data.json (e.g. a crafted sessionId containing <script>).
function esc(value) {
  if (value === null || value === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(value);
  return div.innerHTML;
}

async function loadData() {
  try {
    const res = await fetch(`data.json?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('No pude cargar data.json:', err);
    renderError(err);
    return null;
  }
}

function renderError(err) {
  const main = document.querySelector('main');
  main.innerHTML = `
    <div class="bg-white border border-err/20 rounded-xl p-8 text-center">
      <h2 class="text-xl font-display mb-2 text-err">No hay datos</h2>
      <p class="text-muted text-sm mb-4">No se encuentra <code class="bg-slate-100 px-1 rounded">dashboard/data.json</code>.</p>
      <p class="text-sm text-muted">Ejecuta primero:</p>
      <pre class="mt-3 bg-slate-50 border border-slate-200 rounded p-3 text-xs inline-block text-left">python3 dashboard/api/build_data.py</pre>
      <p class="text-xs text-muted mt-6">Error: ${esc(err.message)}</p>
    </div>
  `;
}

function fmt(n) {
  return new Intl.NumberFormat('es-ES').format(n);
}

function fmtDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('es-ES', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

function relTime(iso) {
  if (!iso) return '-';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'hace segundos';
  if (diff < 3600) return `hace ${Math.round(diff / 60)} min`;
  if (diff < 86400) return `hace ${Math.round(diff / 3600)} h`;
  return `hace ${Math.round(diff / 86400)} d`;
}

function renderHeader(data) {
  document.getElementById('data-source').textContent = data.cognitioDir || '';
  document.getElementById('generated-at').textContent = `Generado ${relTime(data.generatedAt)}`;

  const phase = (data.status && data.status.currentPhase) || 'unknown';
  const phaseColor = PALETTE.phases[phase] || PALETTE.muted;
  document.getElementById('status-phase').innerHTML = `
    <span class="w-2 h-2 rounded-full" style="background:${esc(phaseColor)}"></span>
    <span class="phase-pill" data-phase="${esc(phase)}">${esc(phase)}</span>
  `;

  const profile = (data.status && data.status.profile) || '-';
  document.getElementById('status-profile').innerHTML = `
    perfil: <strong>${esc(profile)}</strong>
  `;
}

function renderKPIs(data) {
  const t = data.totals;
  const container = document.getElementById('kpis');
  container.innerHTML = `
    <div class="kpi">
      <div class="label">Sesiones</div>
      <div class="value">${fmt(t.sessions)}</div>
      <div class="sub">cerradas con éxito</div>
    </div>
    <div class="kpi">
      <div class="label">Modos activos</div>
      <div class="value">${fmt(t.modesUsed)}<span class="text-base text-muted font-normal">/7</span></div>
      <div class="sub">distintos usados</div>
    </div>
    <div class="kpi">
      <div class="label">Gates disparados</div>
      <div class="value">${fmt(t.gatesTriggered)}</div>
      <div class="sub">anti-patrones bloqueados</div>
    </div>
    <div class="kpi">
      <div class="label">Detecciones fase</div>
      <div class="value">${fmt(t.phaseDetections)}</div>
      <div class="sub">sugerencias de cambio</div>
    </div>
  `;
}

function renderModesChart(data) {
  const ctx = document.getElementById('chart-modes').getContext('2d');
  if (charts.modes) charts.modes.destroy();
  const modes = data.modeUsage || [];
  charts.modes = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: modes.map(m => m.mode),
      datasets: [{
        data: modes.map(m => m.count),
        backgroundColor: PALETTE.primary,
        borderRadius: 6,
      }],
    },
    options: {
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b' } },
        y: { grid: { display: false }, ticks: { color: '#0f172a', font: { weight: '500' } } },
      },
    },
  });
}

function renderPhasesChart(data) {
  const ctx = document.getElementById('chart-phases').getContext('2d');
  if (charts.phases) charts.phases.destroy();
  const phases = data.phaseDistribution || [];
  charts.phases = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: phases.map(p => p.phase),
      datasets: [{
        data: phases.map(p => p.sessions),
        backgroundColor: phases.map(p => PALETTE.phases[p.phase] || PALETTE.muted),
        borderWidth: 2,
        borderColor: 'white',
      }],
    },
    options: {
      plugins: {
        legend: { position: 'right', labels: { color: '#0f172a', padding: 12, font: { size: 12 } } },
      },
      cutout: '65%',
    },
  });
}

function renderTimelineChart(data) {
  const ctx = document.getElementById('chart-timeline').getContext('2d');
  if (charts.timeline) charts.timeline.destroy();
  const timeline = data.activityTimeline || [];
  charts.timeline = new Chart(ctx, {
    type: 'line',
    data: {
      labels: timeline.map(d => d.date.slice(5)),  // MM-DD
      datasets: [
        {
          label: 'Sesiones',
          data: timeline.map(d => d.sessions),
          borderColor: PALETTE.primary,
          backgroundColor: PALETTE.primary + '20',
          tension: 0.3,
          fill: true,
        },
        {
          label: 'Gates',
          data: timeline.map(d => d.gates),
          borderColor: PALETTE.err,
          backgroundColor: 'transparent',
          tension: 0.3,
        },
        {
          label: 'Inyecciones',
          data: timeline.map(d => d.injections),
          borderColor: PALETTE.secondary,
          backgroundColor: 'transparent',
          tension: 0.3,
        },
      ],
    },
    options: {
      plugins: {
        legend: { position: 'top', labels: { color: '#0f172a', padding: 12, font: { size: 11 } } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } },
        y: { grid: { color: '#f1f5f9' }, ticks: { color: '#94a3b8' } },
      },
    },
  });
}

function renderGates(data) {
  const container = document.getElementById('gates-list');
  const gates = (data.gatesBreakdown || []).slice(0, 10);
  if (gates.length === 0) {
    container.innerHTML = '<div class="empty">Sin gates disparados (todo limpio)</div>';
    return;
  }
  const max = Math.max(...gates.map(g => g.count));
  container.innerHTML = gates.map(g => {
    const pct = Number.isFinite(max) && max > 0 ? (g.count / max) * 100 : 0;
    return `
    <div class="gate-row">
      <div class="flex-1 min-w-0">
        <code class="block truncate">${esc(g.gate)}</code>
        <div class="mt-1 h-1 bg-slate-100 rounded overflow-hidden">
          <div style="width:${pct.toFixed(2)}%" class="h-full bg-err/60"></div>
        </div>
      </div>
      <span class="count ml-3">${fmt(g.count)}</span>
    </div>
  `;
  }).join('');
}

function renderSinapsis(data) {
  const badge = document.getElementById('sinapsis-badge');
  const details = document.getElementById('sinapsis-details');
  const s = data.status.sinapsisBridge || {};

  if (s.available) {
    const versionLabel = s.version ? 'v' + esc(s.version) : '';
    badge.innerHTML = `<span class="chip ok">Activo ${versionLabel}</span>`;
    details.innerHTML = `
      <p>Bridge conectado. Modos Ejecutor, Verificador y Auditor pueden leer instincts aprendidos.</p>
      <div class="mt-3 grid grid-cols-3 gap-4 text-center">
        <div>
          <div class="text-2xl font-semibold text-ink">${fmt(s.instincts || 0)}</div>
          <div class="text-xs text-muted">instincts activos</div>
        </div>
        <div>
          <div class="text-2xl font-semibold text-ink">${esc(s.version || '?')}</div>
          <div class="text-xs text-muted">version</div>
        </div>
        <div>
          <div class="text-2xl font-semibold text-ok">OK</div>
          <div class="text-xs text-muted">auto-detectado</div>
        </div>
      </div>
    `;
  } else {
    badge.innerHTML = `<span class="chip">Standalone</span>`;
    details.innerHTML = `
      <p>Cognitio funciona en modo standalone. Sinapsis no esta instalado o esta deshabilitado.</p>
      <p class="mt-2 text-xs">Para conectar: instala Sinapsis o edita <code class="bg-slate-100 px-1 rounded">config/_operator-config.json -> integrations.sinapsis</code>.</p>
    `;
  }
}

function renderSessions(data) {
  const tbody = document.getElementById('sessions-table');
  const sessions = data.recentSessions || [];
  if (sessions.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty">Aún no hay sesiones registradas</td></tr>`;
    return;
  }
  tbody.innerHTML = sessions.map(s => {
    const m = s.metrics || {};
    const phase = s.phaseAtClose || 'unknown';
    return `
      <tr class="hover:bg-slate-50">
        <td class="py-2 pr-3"><code class="text-xs">${esc(s.sessionId)}</code></td>
        <td class="py-2 pr-3 text-xs text-muted">${esc(relTime(s.closedAt))}</td>
        <td class="py-2 pr-3"><span class="phase-pill" data-phase="${esc(phase)}">${esc(phase)}</span></td>
        <td class="py-2 text-right font-mono text-xs">${fmt(m.gatesTriggered || 0)}</td>
        <td class="py-2 text-right font-mono text-xs">${fmt(m.modeInjections || 0)}</td>
        <td class="py-2 text-right font-mono text-xs">${fmt(m.phaseDetections || 0)}</td>
      </tr>
    `;
  }).join('');
}

async function render() {
  const data = await loadData();
  if (!data) return;

  renderHeader(data);
  renderKPIs(data);
  renderModesChart(data);
  renderPhasesChart(data);
  renderTimelineChart(data);
  renderGates(data);
  renderSinapsis(data);
  renderSessions(data);
}

document.getElementById('btn-refresh').addEventListener('click', render);
render();
