(function () {
  'use strict';

  const DATA_URL = 'output/warriors-2025-26/dashboard.json';

  function emptySplit(name) {
    return { split: name, makes: 0, attempts: 0, misses: 0, pct: null };
  }

  function getSplit(splits, name) {
    return (splits || []).find((item) => item.split === name) || emptySplit(name);
  }

  function summarizeAttempts(attempts) {
    const total = attempts.length;
    const makes = attempts.reduce((sum, attempt) => sum + (attempt.made ? 1 : 0), 0);
    return {
      makes,
      attempts: total,
      misses: total - makes,
      pct: total ? Math.round((makes / total) * 1000) / 10 : null,
    };
  }

  function filterAttempts(attempts, filters = {}) {
    const search = String(filters.search || '').trim().toLowerCase();
    return (attempts || []).filter((attempt) => {
      if (filters.player && filters.player !== 'all' && attempt.player_name !== filters.player) return false;
      if (filters.segment && filters.segment !== 'all' && attempt.segment !== filters.segment) return false;
      if (filters.venue && filters.venue !== 'all' && attempt.venue !== filters.venue) return false;
      if (filters.position && filters.position !== 'all' && attempt.position !== filters.position) return false;
      if (filters.interrupted === 'yes' && !attempt.interrupted) return false;
      if (filters.interrupted === 'no' && attempt.interrupted) return false;
      if (filters.result === 'made' && !attempt.made) return false;
      if (filters.result === 'missed' && attempt.made) return false;
      if (search) {
        const haystack = [attempt.player_name, attempt.opponent, attempt.description, attempt.trip_type, attempt.position, attempt.interruptions]
          .join(' ')
          .toLowerCase();
        if (!haystack.includes(search)) return false;
      }
      return true;
    });
  }

  function sortPlayersByVolume(players) {
    return [...(players || [])].sort((a, b) => getSplit(b.splits, 'overall').attempts - getSplit(a.splits, 'overall').attempts);
  }

  function paginate(items, requestedPage, pageSize) {
    const pages = Math.max(1, Math.ceil(items.length / pageSize));
    const page = Math.min(Math.max(1, requestedPage || 1), pages);
    const start = (page - 1) * pageSize;
    return { items: items.slice(start, start + pageSize), page, pages, total: items.length };
  }

  function summarizeValidation(rows) {
    const items = rows || [];
    return { passed: items.filter((row) => row.passed).length, total: items.length };
  }

  const api = { getSplit, filterAttempts, summarizeAttempts, sortPlayersByVolume, paginate, summarizeValidation };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;

  const appState = {
    data: null,
    view: 'overview',
    player: 'Stephen Curry',
    compare: ['Stephen Curry', 'Jimmy Butler III'],
    global: { segment: 'all', venue: 'all' },
    attempts: { player: 'all', segment: 'all', venue: 'all', position: 'all', interrupted: 'all', result: 'all', search: '' },
    page: 1,
    pageSize: 30,
  };

  const $ = (selector) => document.querySelector(selector);
  const fmt = new Intl.NumberFormat('en-US');
  const pct = (value) => value == null ? 'N/A' : `${value.toFixed(1)}%`;
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  const initials = (name) => name.split(/\s+/).map((part) => part[0]).join('').slice(0, 3).toUpperCase();

  function summaryCard(label, summary, accent = '') {
    return `<article class="kpi ${accent}"><span>${esc(label)}</span><strong>${pct(summary.pct)}</strong><small>${fmt.format(summary.makes)} / ${fmt.format(summary.attempts)}</small></article>`;
  }

  function currentAttempts(player = null) {
    return filterAttempts(appState.data.attempts, {
      player: player || 'all',
      segment: appState.global.segment,
      venue: appState.global.venue,
    });
  }

  function subset(attempts, predicate) {
    return summarizeAttempts(attempts.filter(predicate));
  }

  function playerRecord(name) {
    return appState.data.players.find((player) => player.player_name === name);
  }

  function splitOptions(values, selected, allLabel) {
    return `<option value="all">${esc(allLabel)}</option>${values.map((value) => `<option value="${esc(value)}" ${value === selected ? 'selected' : ''}>${esc(value)}</option>`).join('')}`;
  }

  function renderSidebar() {
    const players = sortPlayersByVolume(appState.data.players);
    $('#player-list').innerHTML = players.map((player) => {
      const overall = getSplit(player.splits, 'overall');
      return `<button class="player-button ${appState.view === 'player' && appState.player === player.player_name ? 'active' : ''}" data-player="${esc(player.player_name)}">
        <span><b>${esc(player.player_name)}</b><small>${pct(overall.pct)}</small></span><em>${fmt.format(overall.attempts)}</em>
      </button>`;
    }).join('');
    $('#player-count').textContent = `${players.length} players`;
  }

  function renderTabs() {
    document.querySelectorAll('[data-view]').forEach((button) => button.classList.toggle('active', button.dataset.view === appState.view));
    document.querySelectorAll('[data-global-filter]').forEach((select) => { select.value = appState.global[select.dataset.globalFilter]; });
  }

  function landscape(players, attempts) {
    const byPlayer = new Map();
    attempts.forEach((attempt) => {
      if (!byPlayer.has(attempt.player_name)) byPlayer.set(attempt.player_name, []);
      byPlayer.get(attempt.player_name).push(attempt);
    });
    const points = players.map((player) => ({ name: player.player_name, ...summarizeAttempts(byPlayer.get(player.player_name) || []) })).filter((item) => item.attempts);
    const maxAttempts = Math.max(...points.map((item) => item.attempts), 1);
    return `<div class="bubble-chart" aria-label="Player free throw accuracy versus volume">
      <div class="chart-y"><span>100%</span><span>85%</span><span>70%</span><span>55%</span></div>
      <div class="bubble-stage">
        ${points.map((item) => {
          const x = 5 + (item.attempts / maxAttempts) * 88;
          const y = 4 + ((100 - item.pct) / 50) * 84;
          const size = 24 + Math.sqrt(item.attempts / maxAttempts) * 24;
          const featured = /Stephen Curry|Jimmy Butler III/.test(item.name) ? ' featured' : '';
          return `<button class="bubble${featured}" data-player="${esc(item.name)}" title="${esc(item.name)}: ${pct(item.pct)} on ${item.attempts} attempts" style="left:${x}%;top:${Math.min(88, y)}%;width:${size}px;height:${size}px"><span>${initials(item.name)}</span></button>`;
        }).join('')}
        <span class="x-start">Lower volume</span><span class="x-end">Higher volume</span>
      </div>
    </div>`;
  }

  function comparisonBars(rows) {
    return `<div class="comparison-bars">${rows.map((row) => `<div class="bar-row">
      <div class="bar-label"><span>${esc(row.label)}</span><b>${pct(row.summary.pct)}</b><small>${row.summary.makes}/${row.summary.attempts}</small></div>
      <div class="bar-track"><i style="width:${row.summary.pct || 0}%"></i></div>
    </div>`).join('')}</div>`;
  }

  function periodChart(attempts) {
    const periods = ['Q1', 'Q2', 'Q3', 'Q4', 'OT1'];
    const rows = periods.map((label) => ({ label, summary: subset(attempts, (attempt) => attempt.period_label === label) })).filter((row) => row.summary.attempts);
    return `<div class="period-chart">${rows.map((row) => `<div class="period-column"><b>${pct(row.summary.pct)}</b><div><i style="height:${Math.max(8, row.summary.pct)}%"></i></div><span>${row.label}</span><small>${row.summary.attempts} FTA</small></div>`).join('')}</div>`;
  }

  function contextTable(attempts) {
    const rows = [
      ['Home', subset(attempts, (a) => a.venue === 'home')],
      ['Away', subset(attempts, (a) => a.venue === 'away')],
      ['Post-timeout', subset(attempts, (a) => a.timeout_before)],
      ['Interrupted', subset(attempts, (a) => a.interrupted)],
      ['Clutch', subset(attempts, (a) => a.clutch)],
      ['And-one', subset(attempts, (a) => a.trip_type === 'and-one')],
      ['Technical', subset(attempts, (a) => a.trip_type === 'technical')],
    ];
    return `<div class="stat-table">${rows.map(([label, item]) => `<div><span>${label}</span><b>${pct(item.pct)}</b><small>${item.makes}/${item.attempts}</small></div>`).join('')}</div>`;
  }

  function renderOverview() {
    const attempts = currentAttempts();
    const overall = summarizeAttempts(attempts);
    const first = subset(attempts, (a) => a.position === '1 of 2');
    const second = subset(attempts, (a) => a.position === '2 of 2');
    const interrupted = subset(attempts, (a) => a.interrupted);
    const clutch = subset(attempts, (a) => a.clutch);
    const afterMake = subset(attempts, (a) => a.position === '2 of 2' && a.previous_result === 'made');
    const afterMiss = subset(attempts, (a) => a.position === '2 of 2' && a.previous_result === 'missed');
    const validation = summarizeValidation(appState.data.validation);
    $('#content').innerHTML = `<section class="view-head"><div><span class="eyebrow">TEAM OVERVIEW</span><h1>${esc(appState.data.metadata.team_name)}</h1><p>${esc(appState.data.metadata.season)} · ${fmt.format(attempts.length)} attempts in the active filters</p></div><span class="quality-badge">✓ ${validation.passed}/${validation.total} games reconciled</span></section>
      <section class="kpi-grid">${summaryCard('Overall FT%', overall)}${summaryCard('First of two', first)}${summaryCard('Second of two', second, 'positive')}${summaryCard('Interrupted', interrupted, 'warning')}${summaryCard('Clutch', clutch)}</section>
      <section class="dashboard-grid">
        <article class="panel landscape"><header><span class="eyebrow">PLAYER LANDSCAPE</span><h2>Accuracy vs. attempt volume</h2><p>Click any bubble to open that player.</p></header>${landscape(appState.data.players, attempts)}</article>
        <article class="panel"><header><span class="eyebrow">ROUTINE EFFECT</span><h2>Where the sequence changes</h2></header>${comparisonBars([{ label: 'First of two', summary: first }, { label: 'Second of two', summary: second }, { label: 'Second after make', summary: afterMake }, { label: 'Second after miss', summary: afterMiss }])}</article>
        <article class="panel findings"><header><span class="eyebrow">KEY FINDINGS</span><h2>What deserves attention</h2></header>${appState.data.team_findings.slice(1, 6).map((finding) => `<div class="finding"><b>${esc(finding.text)}</b><small>${esc(finding.qualifier)}</small></div>`).join('')}</article>
        <article class="panel periods"><header><span class="eyebrow">QUARTER PROFILE</span><h2>Accuracy by period</h2></header>${periodChart(attempts)}</article>
        <article class="panel contexts"><header><span class="eyebrow">CONTEXT SNAPSHOT</span><h2>Situational results</h2></header>${contextTable(attempts)}</article>
      </section>`;
  }

  function advancedSplitGrid(player) {
    const ordered = [...player.splits].sort((a, b) => b.attempts - a.attempts);
    return `<div class="split-grid">${ordered.map((item) => `<div class="split-card"><span>${esc(item.split)}</span><b>${pct(item.pct)}</b><small>${item.makes}/${item.attempts}</small></div>`).join('')}</div>`;
  }

  function renderPlayer() {
    const player = playerRecord(appState.player) || sortPlayersByVolume(appState.data.players)[0];
    appState.player = player.player_name;
    const attempts = currentAttempts(player.player_name);
    const overall = summarizeAttempts(attempts);
    const first = subset(attempts, (a) => a.position === '1 of 2');
    const second = subset(attempts, (a) => a.position === '2 of 2');
    const afterMake = subset(attempts, (a) => a.position === '2 of 2' && a.previous_result === 'made');
    const afterMiss = subset(attempts, (a) => a.position === '2 of 2' && a.previous_result === 'missed');
    const immediate = subset(attempts, (a) => !a.interrupted);
    const interrupted = subset(attempts, (a) => a.interrupted);
    $('#content').innerHTML = `<section class="view-head"><div><button class="back-link" data-view="overview">← Team overview</button><span class="eyebrow">PLAYER DETAIL</span><h1>${esc(player.player_name)}</h1><p>${fmt.format(attempts.length)} attempts in the active filters</p></div><button class="primary-button" data-jump-attempts="${esc(player.player_name)}">Explore attempts</button></section>
      <section class="kpi-grid">${summaryCard('Overall FT%', overall)}${summaryCard('First of two', first)}${summaryCard('Second of two', second)}${summaryCard('Immediate', immediate)}${summaryCard('Interrupted', interrupted, 'warning')}</section>
      <section class="player-grid">
        <article class="panel"><header><span class="eyebrow">SEQUENCE PROFILE</span><h2>Attempt order and prior result</h2></header>${comparisonBars([{ label: 'First of two', summary: first }, { label: 'Second of two', summary: second }, { label: 'Second after make', summary: afterMake }, { label: 'Second after miss', summary: afterMiss }])}</article>
        <article class="panel"><header><span class="eyebrow">PERIOD PROFILE</span><h2>Accuracy by quarter</h2></header>${periodChart(attempts)}</article>
        <article class="panel findings"><header><span class="eyebrow">PLAYER FINDINGS</span><h2>Evidence-backed notes</h2></header>${player.findings.map((finding) => `<div class="finding"><b>${esc(finding.text)}</b><small>${esc(finding.qualifier)}</small></div>`).join('')}</article>
        <article class="panel full-width"><header><span class="eyebrow">EVERY CLASSIFIED SPLIT</span><h2>Full-season reference</h2><p>All available attempt order, interruption, location, score, quarter, trip type, and workload splits.</p></header>${advancedSplitGrid(player)}</article>
      </section>`;
  }

  const compareMetrics = [
    ['Overall', 'overall'], ['Home', 'home'], ['Away', 'away'], ['First of two', '1 of 2'], ['Second of two', '2 of 2'],
    ['After first make', '2 of 2 after made'], ['After first miss', '2 of 2 after missed'], ['Immediate', 'immediate'], ['Interrupted', 'interrupted'],
    ['Clutch', 'clutch'], ['Stint 0–5m', 'stint 0-5m'], ['Stint 10m+', 'stint 10m+'], ['Played 30m+', 'played 30m+'],
  ];

  function renderCompare() {
    const players = sortPlayersByVolume(appState.data.players);
    const [leftName, rightName] = appState.compare;
    const left = playerRecord(leftName) || players[0];
    const right = playerRecord(rightName) || players[1];
    const options = (selected) => players.map((player) => `<option ${player.player_name === selected ? 'selected' : ''}>${esc(player.player_name)}</option>`).join('');
    $('#content').innerHTML = `<section class="view-head"><div><span class="eyebrow">COMPARISON LAB</span><h1>Player vs. player</h1><p>Full-season splits with sample sizes retained.</p></div></section>
      <section class="compare-selectors"><label>Player A<select data-compare="0">${options(left.player_name)}</select></label><span>VS</span><label>Player B<select data-compare="1">${options(right.player_name)}</select></label></section>
      <section class="panel compare-table"><div class="compare-head"><b>Context</b><b>${esc(left.player_name)}</b><b>${esc(right.player_name)}</b><b>Edge</b></div>${compareMetrics.map(([label, key]) => {
        const a = getSplit(left.splits, key); const b = getSplit(right.splits, key);
        const delta = a.pct == null || b.pct == null ? null : Math.round((a.pct - b.pct) * 10) / 10;
        return `<div class="compare-row"><strong>${esc(label)}</strong><div><b>${pct(a.pct)}</b><small>${a.makes}/${a.attempts}</small></div><div><b>${pct(b.pct)}</b><small>${b.makes}/${b.attempts}</small></div><span class="edge ${delta > 0 ? 'left' : delta < 0 ? 'right' : ''}">${delta == null ? 'N/A' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)} A`}</span></div>`;
      }).join('')}</section>`;
  }

  function attemptFilterControls() {
    const players = sortPlayersByVolume(appState.data.players).map((player) => player.player_name);
    const positions = [...new Set(appState.data.attempts.map((a) => a.position))].sort();
    return `<div class="filter-grid">
      <label>Player<select data-attempt-filter="player">${splitOptions(players, appState.attempts.player, 'All players')}</select></label>
      <label>Segment<select data-attempt-filter="segment">${splitOptions(['Regular Season', 'Play-In', 'Playoffs'], appState.attempts.segment, 'All segments')}</select></label>
      <label>Venue<select data-attempt-filter="venue">${splitOptions(['home', 'away'], appState.attempts.venue, 'Home + away')}</select></label>
      <label>Attempt type<select data-attempt-filter="position">${splitOptions(positions, appState.attempts.position, 'All positions')}</select></label>
      <label>Interruption<select data-attempt-filter="interrupted">${splitOptions(['yes', 'no'], appState.attempts.interrupted, 'Either')}</select></label>
      <label>Result<select data-attempt-filter="result">${splitOptions(['made', 'missed'], appState.attempts.result, 'Makes + misses')}</select></label>
      <label class="search-label">Search<input data-attempt-search type="search" value="${esc(appState.attempts.search)}" placeholder="Opponent, description, trip type…"></label>
    </div>`;
  }

  function renderAttempts() {
    const filtered = filterAttempts(appState.data.attempts, appState.attempts);
    const result = paginate(filtered, appState.page, appState.pageSize);
    appState.page = result.page;
    const summary = summarizeAttempts(filtered);
    $('#content').innerHTML = `<section class="view-head"><div><span class="eyebrow">ATTEMPT EXPLORER</span><h1>Every official free throw</h1><p>${fmt.format(result.total)} matching attempts · ${pct(summary.pct)} · ${summary.makes}/${summary.attempts}</p></div><button class="primary-button" data-export>Export filtered CSV</button></section>
      <section class="panel filters-panel">${attemptFilterControls()}</section>
      <section class="panel attempt-panel"><div class="table-scroll"><table class="attempt-table"><thead><tr><th>Date</th><th>Player</th><th>Game</th><th>Attempt</th><th>Result</th><th>Context</th><th>Workload</th></tr></thead><tbody>${result.items.map((a) => `<tr><td>${esc(a.date)}</td><td><b>${esc(a.player_name)}</b></td><td>${esc(a.venue === 'home' ? 'vs' : '@')} ${esc(a.opponent)}<small>${esc(a.segment)} · ${esc(a.period_label)} ${esc(a.clock)}</small></td><td>${esc(a.position)}<small>${esc(a.trip_type)}</small></td><td><span class="result ${a.made ? 'made' : 'missed'}">${a.made ? 'MAKE' : 'MISS'}</span></td><td>${a.interrupted ? '<span class="context-chip warning">Interrupted</span>' : '<span class="context-chip">Immediate</span>'}${a.clutch ? '<span class="context-chip gold">Clutch</span>' : ''}${a.timeout_before ? '<span class="context-chip">Post-timeout</span>' : ''}<small>${esc(a.description)}</small></td><td>${Math.round((a.continuous_stint_seconds || 0) / 60)}m stint<small>${Math.round((a.cumulative_seconds_played || 0) / 60)}m played</small></td></tr>`).join('')}</tbody></table></div>
      <div class="pager"><button data-page="${result.page - 1}" ${result.page <= 1 ? 'disabled' : ''}>← Previous</button><span>Page ${result.page} of ${result.pages}</span><button data-page="${result.page + 1}" ${result.page >= result.pages ? 'disabled' : ''}>Next →</button></div></section>`;
  }

  function render() {
    renderSidebar();
    renderTabs();
    if (appState.view === 'player') renderPlayer();
    else if (appState.view === 'compare') renderCompare();
    else if (appState.view === 'attempts') renderAttempts();
    else renderOverview();
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  function csvCell(value) {
    const text = String(value ?? '');
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function exportAttempts() {
    const rows = filterAttempts(appState.data.attempts, appState.attempts);
    const keys = ['date', 'segment', 'player_name', 'opponent', 'venue', 'period_label', 'clock', 'position', 'previous_result', 'trip_type', 'made', 'interrupted', 'interruptions', 'clutch', 'continuous_stint_seconds', 'cumulative_seconds_played', 'description'];
    const csv = [keys.join(','), ...rows.map((row) => keys.map((key) => csvCell(row[key])).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'warriors-free-throws-filtered.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function bindEvents() {
    document.addEventListener('click', (event) => {
      const view = event.target.closest('[data-view]');
      if (view) { appState.view = view.dataset.view; render(); return; }
      const player = event.target.closest('[data-player]');
      if (player) { appState.player = player.dataset.player; appState.view = 'player'; render(); return; }
      const attempts = event.target.closest('[data-jump-attempts]');
      if (attempts) { appState.attempts.player = attempts.dataset.jumpAttempts; appState.page = 1; appState.view = 'attempts'; render(); return; }
      const page = event.target.closest('[data-page]');
      if (page && !page.disabled) { appState.page = Number(page.dataset.page); renderAttempts(); return; }
      if (event.target.closest('[data-export]')) exportAttempts();
      if (event.target.closest('[data-sidebar-toggle]')) document.body.classList.toggle('sidebar-open');
    });
    document.addEventListener('change', (event) => {
      if (event.target.matches('[data-global-filter]')) { appState.global[event.target.dataset.globalFilter] = event.target.value; render(); }
      if (event.target.matches('[data-attempt-filter]')) { appState.attempts[event.target.dataset.attemptFilter] = event.target.value; appState.page = 1; renderAttempts(); }
      if (event.target.matches('[data-compare]')) { appState.compare[Number(event.target.dataset.compare)] = event.target.value; renderCompare(); }
    });
    document.addEventListener('input', (event) => {
      if (event.target.matches('[data-attempt-search]')) { appState.attempts.search = event.target.value; appState.page = 1; renderAttempts(); const input = $('[data-attempt-search]'); input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
    });
  }

  async function init() {
    bindEvents();
    try {
      const response = await fetch(DATA_URL);
      if (!response.ok) throw new Error(`Data request failed with ${response.status}`);
      appState.data = await response.json();
      $('#loading').remove();
      render();
    } catch (error) {
      $('#loading').innerHTML = `<div class="load-error"><b>Dashboard data could not be loaded.</b><span>${esc(error.message)}</span><small>Open this page through GitHub Pages or a local HTTP server.</small></div>`;
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
