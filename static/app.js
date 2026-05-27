// ─── State ────────────────────────────────────────────────────────────────────
const state = {
  options: { teams: [], venues: [] },
  data: null,
  filters: { teams: [], venues: [] },
  page: "home",
  theme: "dark",
  chat: [{ speaker: "bot", text: "Welcome! I'm your IPL expert 🏏 Ask me about teams, players, history, records — anything IPL! Try the suggestion buttons below to start." }],
  recordsLoaded: false,
  seasonsLoaded: false,
};

// ─── Team meta (colours + abbreviations) ─────────────────────────────────────
const TEAM_META = {
  "Chennai Super Kings":           { colors: ["#f7d417","#1f3c88"], abbr: "CSK" },
  "Mumbai Indians":                { colors: ["#005da8","#d8a928"], abbr: "MI"  },
  "Royal Challengers Bangalore":   { colors: ["#c8102e","#111111"], abbr: "RCB" },
  "Royal Challengers Bengaluru":   { colors: ["#c8102e","#111111"], abbr: "RCB" },
  "Kolkata Knight Riders":         { colors: ["#3a225d","#d4af37"], abbr: "KKR" },
  "Rajasthan Royals":              { colors: ["#ea1a85","#254aa5"], abbr: "RR"  },
  "Delhi Capitals":                { colors: ["#17479e","#ef1b23"], abbr: "DC"  },
  "Delhi Daredevils":              { colors: ["#17479e","#ef1b23"], abbr: "DD"  },
  "Sunrisers Hyderabad":           { colors: ["#f26522","#111111"], abbr: "SRH" },
  "Punjab Kings":                  { colors: ["#d71920","#f6c343"], abbr: "PBKS"},
  "Kings XI Punjab":               { colors: ["#d71920","#f6c343"], abbr: "KXIP"},
  "Gujarat Titans":                { colors: ["#1c2841","#b9945c"], abbr: "GT"  },
  "Lucknow Super Giants":          { colors: ["#00a3e0","#f58220"], abbr: "LSG" },
  "Deccan Chargers":               { colors: ["#283891","#c7a34b"], abbr: "DC2" },
  "Pune Warriors":                 { colors: ["#00a0df","#f15a24"], abbr: "PW"  },
  "Rising Pune Supergiants":       { colors: ["#7a4fb3","#f47c20"], abbr: "RPS" },
  "Rising Pune Supergiant":        { colors: ["#7a4fb3","#f47c20"], abbr: "RPS" },
  "Gujarat Lions":                 { colors: ["#f47c20","#203864"], abbr: "GL"  },
  "Kochi Tuskers Kerala":          { colors: ["#f58220","#6a1b9a"], abbr: "KTK" },
};

// ─── Wikipedia team logos (primary) ──────────────────────────────────────────
const WIKI_LOGOS = {
  "Chennai Super Kings":           "https://upload.wikimedia.org/wikipedia/en/2/2b/Chennai_Super_Kings_Logo.svg",
  "Mumbai Indians":                "https://upload.wikimedia.org/wikipedia/en/c/cd/Mumbai_Indians_Logo.svg",
  "Royal Challengers Bangalore":   "https://upload.wikimedia.org/wikipedia/en/2/2a/Royal_Challengers_Bangalore_2020.svg",
  "Royal Challengers Bengaluru":   "https://upload.wikimedia.org/wikipedia/en/2/2a/Royal_Challengers_Bangalore_2020.svg",
  "Kolkata Knight Riders":         "https://upload.wikimedia.org/wikipedia/en/4/4c/Kolkata_Knight_Riders_Logo.svg",
  "Rajasthan Royals":              "https://upload.wikimedia.org/wikipedia/en/6/60/Rajasthan_Royals_Logo.svg",
  "Delhi Capitals":                "https://upload.wikimedia.org/wikipedia/en/0/0e/Delhi_Capitals_Logo.svg",
  "Delhi Daredevils":              "https://upload.wikimedia.org/wikipedia/en/3/3f/Delhidaredevils.png",
  "Sunrisers Hyderabad":           "https://upload.wikimedia.org/wikipedia/en/3/3b/Sunrisers_Hyderabad.svg",
  "Punjab Kings":                  "https://upload.wikimedia.org/wikipedia/en/d/d4/Punjab_Kings_Logo.svg",
  "Kings XI Punjab":               "https://upload.wikimedia.org/wikipedia/en/d/d4/Punjab_Kings_Logo.svg",
  "Gujarat Titans":                "https://upload.wikimedia.org/wikipedia/en/0/09/Gujarat_Titans_Logo.svg",
  "Lucknow Super Giants":          "https://upload.wikimedia.org/wikipedia/en/b/b9/Lucknow_Super_Giants_Logo.svg",
  "Deccan Chargers":               "https://upload.wikimedia.org/wikipedia/en/a/a8/Deccan_Chargers_Logo.png",
  "Rising Pune Supergiants":       "https://upload.wikimedia.org/wikipedia/en/9/96/Rising_Pune_Supergiants_Logo.png",
  "Rising Pune Supergiant":        "https://upload.wikimedia.org/wikipedia/en/9/96/Rising_Pune_Supergiants_Logo.png",
  "Gujarat Lions":                 "https://upload.wikimedia.org/wikipedia/en/3/39/Gujarat_Lions_Logo.png",
};

const FALLBACK_PALETTES = [
  ["#0ea5e9","#7c3aed"], ["#ef4444","#f97316"], ["#14b8a6","#2563eb"],
  ["#a855f7","#ec4899"], ["#16a34a","#65a30d"], ["#f59e0b","#dc2626"],
];

function teamMeta(name) {
  if (TEAM_META[name]) return TEAM_META[name];
  const seed = String(name).split("").reduce((s, c) => s + c.charCodeAt(0), 0);
  const colors = FALLBACK_PALETTES[seed % FALLBACK_PALETTES.length];
  const abbr = String(name).split(/\s+/).filter(w => w.length > 1).map(w => w[0]).join("").slice(0, 4).toUpperCase();
  return { colors, abbr };
}

// Generate inline SVG data-URI badge as fallback
function makeTeamBadge(name) {
  const { colors: [c1, c2], abbr } = teamMeta(name);
  const fs = abbr.length > 3 ? 15 : abbr.length === 3 ? 18 : 22;
  const gid = `tg${Math.random().toString(36).slice(2, 7)}`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
    <defs>
      <linearGradient id="${gid}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:${c1}"/>
        <stop offset="100%" style="stop-color:${c2}"/>
      </linearGradient>
    </defs>
    <circle cx="40" cy="40" r="38" fill="url(#${gid})" stroke="rgba(255,255,255,0.45)" stroke-width="2.5"/>
    <circle cx="40" cy="40" r="30" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>
    <text x="40" y="48" text-anchor="middle" fill="white"
      font-family="Bebas Neue,Arial Black,sans-serif"
      font-size="${fs}" font-weight="bold" letter-spacing="1">${escapeHtml(abbr)}</text>
  </svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

// Return <img> tag: try wiki logo, fall back to SVG badge
function teamLogoImg(name, cls = "team-logo") {
  const wiki = WIKI_LOGOS[name];
  const badge = makeTeamBadge(name);
  const abbr = teamMeta(name).abbr;
  if (wiki) {
    return `<img class="${cls}" src="${escapeHtml(wiki)}" alt="${escapeHtml(abbr)} logo" onerror="this.onerror=null;this.src='${badge}'" loading="lazy" />`;
  }
  return `<img class="${cls}" src="${badge}" alt="${escapeHtml(abbr)} badge" />`;
}

// ─── Chat suggestions ─────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "What is IPL?",
  "Who has won the most titles?",
  "Which batter scored the most runs?",
  "Which bowler has the most wickets?",
  "Does winning the toss help?",
  "What is T20 cricket?",
  "Which venue is best for chasing?",
  "Tell me about Dhoni",
  "Tell me about Virat Kohli",
  "How does the IPL auction work?",
  "What are the all-time records?",
  "Fun facts about IPL",
];

// ─── Utilities ────────────────────────────────────────────────────────────────
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

function pct(v) { return `${((Number(v) || 0) * 100).toFixed(1)}%`; }
function num(v, d = 0) {
  if (v == null || Number.isNaN(Number(v))) return "-";
  return Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
}
function escapeHtml(v) {
  return String(v ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
function selectedValues(sel) { return [...sel.selectedOptions].map(o => o.value); }
function setOptions(sel, vals, chosen = []) {
  sel.innerHTML = vals.map(v =>
    `<option value="${escapeHtml(v)}"${chosen.includes(v) ? " selected" : ""}>${escapeHtml(v)}</option>`
  ).join("");
}

// Compute left-margin for horizontal bar labels
function leftPad(labels) {
  if (!labels || !labels.length) return 80;
  const max = Math.max(...labels.map(l => String(l ?? "").length));
  return Math.min(Math.max(max * 7 + 24, 70), 340);
}

// Medal for rank 1/2/3
function medal(rank) {
  if (rank === 1) return `<span class="record-pos gold">🥇</span>`;
  if (rank === 2) return `<span class="record-pos silver">🥈</span>`;
  if (rank === 3) return `<span class="record-pos bronze">🥉</span>`;
  return `<span class="record-pos">${rank}</span>`;
}

// ─── Chart theme ──────────────────────────────────────────────────────────────
function chartTheme() {
  const dark = state.theme === "dark";
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor:  dark ? "rgba(8,11,23,0.4)" : "rgba(255,255,255,0.9)",
    font: { color: dark ? "#f8fafc" : "#101827", family: "Inter,sans-serif", size: 11 },
    legend: { orientation: "h", yanchor: "bottom", y: 1.02, xanchor: "right", x: 1 },
    xaxis: { gridcolor: dark ? "rgba(226,232,240,0.1)" : "rgba(15,23,42,0.08)", zeroline: false },
    yaxis: { gridcolor: dark ? "rgba(226,232,240,0.1)" : "rgba(15,23,42,0.08)", automargin: true },
    hoverlabel: {
      bgcolor:     dark ? "#1e2d40" : "#ffffff",
      font:        { color: dark ? "#f8fafc" : "#0f172a", size: 12 },
      bordercolor: dark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.1)",
    },
  };
}

function plot(id, traces, layout, cfg = {}) {
  Plotly.react(id, traces, { ...chartTheme(), ...layout }, { responsive: true, displaylogo: false, ...cfg });
}

// ─── Animated counter ─────────────────────────────────────────────────────────
function animateCounter(el, target, duration = 1100) {
  const t0 = performance.now();
  const fmt = Number.isInteger(target)
    ? v => Number(Math.round(v)).toLocaleString("en-IN")
    : v => v.toFixed(1);
  (function step(now) {
    const p = Math.min((now - t0) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = fmt(target * eased);
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = fmt(target);
  })(t0);
}

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  const opts = await fetch("/api/options").then(r => r.json());
  state.options = opts;
  setOptions($("#teamFilter"),  opts.teams,  []);
  setOptions($("#venueFilter"), opts.venues, []);
  wireEvents();
  renderSuggestions();
  await loadDashboard({ showOverlay: true });
}

// ─── Events ───────────────────────────────────────────────────────────────────
function wireEvents() {
  $$(".nav-button, .jump-button, .back-button").forEach(b =>
    b.addEventListener("click", () => showPage(b.dataset.page))
  );

  $("#applyFilters").addEventListener("click", async () => {
    state.filters = {
      teams:  selectedValues($("#teamFilter")),
      venues: selectedValues($("#venueFilter")),
    };
    await loadDashboard();
  });

  $("#resetFilters").addEventListener("click", async () => {
    state.filters = { teams: [], venues: [] };
    setOptions($("#teamFilter"),  state.options.teams,  []);
    setOptions($("#venueFilter"), state.options.venues, []);
    await loadDashboard();
  });

  $("#themeToggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    document.body.dataset.theme = state.theme;
    $("#themeToggle").textContent = state.theme === "dark" ? "☀️ Light" : "🌙 Dark";
    if (state.data) renderAll();
  });

  // Live table search
  ["batterSearch", "bowlerSearch", "teamSearch", "venueSearch"].forEach(id => {
    const el = $(`#${id}`);
    if (el) el.addEventListener("input", () => state.data && renderTables());
  });

  $("#sendChat").addEventListener("click", sendChat);
  $("#chatInput").addEventListener("keydown", e => { if (e.key === "Enter") sendChat(); });
}

function showPage(page) {
  if (!page) return;
  state.page = page;
  $$(".page").forEach(s => s.classList.toggle("active", s.id === page));
  $$(".nav-button").forEach(b => b.classList.toggle("active", b.dataset.page === page));
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Lazy-load records & seasons on first visit
  if (page === "records" && !state.recordsLoaded) loadRecords();
  if (page === "seasons" && !state.seasonsLoaded) loadSeasons();

  setTimeout(() => {
    if (state.data) renderCharts();
    initScrollReveal();
  }, 80);
}

// ─── Load dashboard data ──────────────────────────────────────────────────────
async function loadDashboard({ showOverlay = false } = {}) {
  const p = new URLSearchParams();
  state.filters.teams.forEach(v => p.append("teams", v));
  state.filters.venues.forEach(v => p.append("venues", v));

  const overlay = $("#loadingOverlay");
  if (overlay) overlay.style.display = showOverlay ? "flex" : "none";

  state.data = await fetch(`/api/dashboard?${p}`).then(r => r.json());

  if (overlay) overlay.style.display = "none";
  renderAll();
}

// ─── Load records ─────────────────────────────────────────────────────────────
async function loadRecords() {
  state.recordsLoaded = true;
  const grid = $("#recordsGrid");
  if (!grid) return;
  grid.innerHTML = `<div class="records-loading">⏳ Loading records…</div>`;

  try {
    const data = await fetch("/api/records").then(r => r.json());
    renderRecordsGrid(data);
  } catch (e) {
    grid.innerHTML = `<div class="records-loading">⚠️ Could not load records. Is the server running?</div>`;
  }
}

function renderRecordsGrid(data) {
  const grid = $("#recordsGrid");
  if (!grid) return;

  const { topInnings = [], topTotals = [], topBowling = [] } = data;

  const inningsHtml = topInnings.map((r, i) => `
    <div class="record-row">
      ${medal(i + 1)}
      <div class="record-name">
        <strong>${escapeHtml(r.batter)}</strong>
        <small>${escapeHtml(r.team_1 || "")} vs ${escapeHtml(r.team_2 || "")} · ${escapeHtml(r.season || "")}</small>
      </div>
      <div class="record-val">
        <span class="rv-main">${num(r.runs)} runs</span>
        <span class="rv-sub">${num(r.balls)} balls · ${num(r.fours)}×4 · ${num(r.sixes)}×6 · SR ${num(r.strike_rate, 1)}</span>
      </div>
    </div>`).join("");

  const totalsHtml = topTotals.map((r, i) => `
    <div class="record-row">
      ${medal(i + 1)}
      <div class="record-name">
        <strong>${escapeHtml(r.batting_team)}</strong>
        <small>${escapeHtml(r.venue || "")} · ${escapeHtml(r.season || "")}</small>
      </div>
      <div class="record-val">
        <span class="rv-main">${num(r.total)} runs</span>
        <span class="rv-sub">1st innings total</span>
      </div>
    </div>`).join("");

  const bowlingHtml = topBowling.map((r, i) => `
    <div class="record-row">
      ${medal(i + 1)}
      <div class="record-name">
        <strong>${escapeHtml(r.bowler)}</strong>
        <small>${escapeHtml(r.venue || "")} · ${escapeHtml(r.season || "")}</small>
      </div>
      <div class="record-val">
        <span class="rv-main">${num(r.wickets)}/${num(r.runs)}</span>
        <span class="rv-sub">${num(r.balls)} balls · ECO ${num(r.economy, 2)}</span>
      </div>
    </div>`).join("");

  grid.innerHTML = `
    <div class="record-block reveal">
      <div class="record-block-header">
        <span class="rb-icon">🏏</span>
        <div>
          <h3>Top Batting Innings</h3>
          <p class="tiny-note">Highest individual scores in a single match</p>
        </div>
      </div>
      ${inningsHtml || `<p class="no-data">No innings data available.</p>`}
    </div>

    <div class="record-block reveal">
      <div class="record-block-header">
        <span class="rb-icon">🏟️</span>
        <div>
          <h3>Highest Team Totals</h3>
          <p class="tiny-note">Biggest 1st innings scores in a single match</p>
        </div>
      </div>
      ${totalsHtml || `<p class="no-data">No team total data available.</p>`}
    </div>

    <div class="record-block reveal">
      <div class="record-block-header">
        <span class="rb-icon">⚡</span>
        <div>
          <h3>Best Bowling Figures</h3>
          <p class="tiny-note">Most wickets taken in a single match</p>
        </div>
      </div>
      ${bowlingHtml || `<p class="no-data">No bowling data available.</p>`}
    </div>`;

  setTimeout(initScrollReveal, 60);
}

// ─── Load seasons ─────────────────────────────────────────────────────────────
async function loadSeasons() {
  state.seasonsLoaded = true;
  const timeline = $("#seasonsTimeline");
  if (!timeline) return;
  timeline.innerHTML = `<div class="records-loading">⏳ Loading season history…</div>`;

  try {
    const data = await fetch("/api/seasons").then(r => r.json());
    renderSeasonsTimeline(data.seasons || []);
  } catch (e) {
    timeline.innerHTML = `<div class="records-loading">⚠️ Could not load seasons. Is the server running?</div>`;
  }
}

function renderSeasonsTimeline(seasons) {
  const timeline = $("#seasonsTimeline");
  if (!timeline) return;
  if (!seasons.length) {
    timeline.innerHTML = `<p class="no-data">No season data found.</p>`;
    return;
  }

  // Header row
  const header = `
    <div class="season-card season-header">
      <span>Season</span>
      <span>Matches</span>
      <span>Top Scorer</span>
      <span>Top Bowler</span>
      <span>Avg 1st Innings</span>
    </div>`;

  const cards = seasons.map(s => {
    const avgRuns = s.avg_runs != null ? num(s.avg_runs, 1) : "-";
    const topScorer = s.top_scorer
      ? `${escapeHtml(s.top_scorer)} <span class="season-stat">${num(s.top_scorer_runs)} runs</span>`
      : "-";
    const topBowler = s.top_bowler
      ? `${escapeHtml(s.top_bowler)} <span class="season-stat">${num(s.top_bowler_wickets)} wkts</span>`
      : "-";
    return `
      <div class="season-card reveal">
        <span class="season-year">${escapeHtml(String(s.season))}</span>
        <span class="season-matches">${num(s.matches)} <small>games</small></span>
        <span class="season-player">${topScorer}</span>
        <span class="season-player">${topBowler}</span>
        <span class="season-runs">${avgRuns}</span>
      </div>`;
  }).join("");

  timeline.innerHTML = header + cards;
  setTimeout(initScrollReveal, 60);
}

// ─── Render all ───────────────────────────────────────────────────────────────
function renderAll() {
  renderMetrics();
  renderTeamCards();
  renderTables();
  renderChat();
  renderTicker();
  renderCharts();
  setTimeout(initScrollReveal, 80);
}

// ─── Metrics ──────────────────────────────────────────────────────────────────
function renderMetrics() {
  const m = state.data.metrics;
  const items = [
    { icon: "🏏", label: "Matches",   val: m.matches,  raw: m.matches,  note: "Games analysed" },
    { icon: "📅", label: "Seasons",   val: m.seasons,  raw: m.seasons,  note: "IPL seasons" },
    { icon: "🏆", label: "Teams",     val: m.teams,    raw: m.teams,    note: "Franchises" },
    { icon: "⭐", label: "Players",   val: m.players,  raw: m.players,  note: "Batters & bowlers" },
    { icon: "🪙", label: "Toss Edge", val: pct(m.tossWinRate), raw: null, note: "Toss winner win %" },
  ];
  $("#metricGrid").innerHTML = items.map(({ icon, label, val, note }) =>
    `<article class="metric-card">
      <div class="metric-icon">${icon}</div>
      <span>${label}</span>
      <strong>${val}</strong>
      <small>${note}</small>
    </article>`
  ).join("");

  items.forEach(({ raw }, i) => {
    if (raw == null || isNaN(raw)) return;
    const el = $("#metricGrid").querySelectorAll("strong")[i];
    animateCounter(el, raw);
  });
}

// ─── Team cards ───────────────────────────────────────────────────────────────
function renderTeamCards() {
  const teams = state.data.teams.slice(0, 8);
  if (!teams.length) { $("#teamCards").innerHTML = "<p>No teams found.</p>"; return; }

  $("#teamCards").innerHTML = teams.map((t, rank) => {
    const { colors: [c1, c2] } = teamMeta(t.team);
    const logoImg = teamLogoImg(t.team, "team-logo");
    const wr = (Number(t.win_rate) || 0) * 100;
    return `
      <article class="team-card" style="--team-a:${c1};--team-b:${c2}" data-page="teams" role="button" tabindex="0">
        <div class="team-rank">#${rank + 1}</div>
        <div class="team-logo-row">
          ${logoImg}
          <div>
            <p class="eyebrow">Team</p>
            <strong class="team-name-text">${escapeHtml(t.team)}</strong>
          </div>
        </div>
        <h4>${pct(t.win_rate)} win rate</h4>
        <p>${num(t.wins)}W / ${num(t.losses)}L in ${num(t.decisive_matches)} decisive</p>
        <div class="win-bar"><div class="win-bar-fill" style="width:${Math.min(wr, 100).toFixed(1)}%"></div></div>
      </article>`;
  }).join("");

  $$(".team-card").forEach(card => {
    card.addEventListener("click", () => showPage("teams"));
    card.addEventListener("keydown", e => { if (e.key === "Enter") showPage("teams"); });
  });
}

// ─── Stats ticker ─────────────────────────────────────────────────────────────
function renderTicker() {
  const d = state.data;
  if (!d) return;
  const items = [];
  const tb = d.batters[0], bw = d.bowlers[0], tt = d.teams[0];
  if (tt) items.push(`🏆 Best Win Rate: ${tt.team} — ${pct(tt.win_rate)}`);
  if (tb) items.push(`🏏 Top Scorer: ${tb.batter} — ${num(tb.runs)} runs @ SR ${num(tb.strike_rate, 1)}`);
  if (bw) items.push(`⚡ Top Wicket-Taker: ${bw.bowler} — ${num(bw.wickets)} wickets @ ECO ${num(bw.economy, 2)}`);
  items.push(`📊 ${num(d.metrics.matches)} matches · ${num(d.metrics.seasons)} seasons · ${num(d.metrics.players)} players`);
  items.push(`🪙 Toss winners won ${pct(d.metrics.tossWinRate)} of decisive matches`);
  items.push(`🌍 IPL — World's No.1 T20 League · $10B+ Valuation · 750M+ Fans`);

  const doubled = [...items, ...items].map(i => `<span class="ticker-item">${escapeHtml(i)}</span>`).join("");
  const el = $("#statsTicker");
  if (el) el.innerHTML = doubled;
}

// ─── Charts ───────────────────────────────────────────────────────────────────
function renderCharts() {
  if (!state.data) return;
  const { teams, teamSeason, batters, bowlers, toss, tossSeason, venues } = state.data;

  /* ── Team win rate ── */
  const tSlice = teams.slice(0, 15).reverse();
  const tLm    = leftPad(tSlice.map(t => t.team));
  const tMax   = Math.max(...tSlice.map(t => Number(t.win_rate) || 0), 0.01);
  plot("teamWinChart",
    [{ type: "bar", orientation: "h",
       x: tSlice.map(t => t.win_rate),
       y: tSlice.map(t => t.team),
       text: tSlice.map(t => pct(t.win_rate)),
       textposition: "outside",
       marker: { color: tSlice.map(t => t.wins),
                 colorscale: [[0,"#1a237e"],[0.45,"#e65100"],[1,"#f9a825"]],
                 showscale: false },
       hovertemplate: "<b>%{y}</b><br>Win Rate: %{text}<br>Wins: %{marker.color}<extra></extra>",
    }],
    { xaxis: { tickformat: ".0%", range: [0, tMax * 1.25], automargin: true },
      yaxis: { automargin: true },
      height: 520, margin: { t: 30, r: 90, b: 40, l: tLm } }
  );

  /* ── Season win-rate lines ── */
  const sRows  = teamSeason.slice(0, 280);
  const sTeams = [...new Set(sRows.map(r => r.team))].slice(0, 10);
  plot("teamSeasonChart",
    sTeams.map(team => {
      const rows = sRows.filter(r => r.team === team);
      const { colors: [c1] } = teamMeta(team);
      return { type: "scatter", mode: "lines+markers", name: team,
               x: rows.map(r => r.season), y: rows.map(r => r.win_rate),
               line: { color: c1, width: 2.5 }, marker: { color: c1, size: 7, line: { color: "#fff", width: 1 } },
               hovertemplate: `<b>${escapeHtml(team)}</b><br>Season: %{x}<br>Win Rate: %{y:.1%}<extra></extra>` };
    }),
    { yaxis: { tickformat: ".0%", automargin: true },
      xaxis: { automargin: true, type: "category" },
      height: 520, margin: { t: 30, r: 24, b: 80, l: 60 } }
  );

  /* ── Top batters ── */
  const bSlice = batters.slice(0, 12).reverse();
  const bLm    = leftPad(bSlice.map(b => b.batter));
  const bMax   = Math.max(...bSlice.map(b => Number(b.runs) || 0), 1);
  plot("batterChart",
    [{ type: "bar", orientation: "h",
       x: bSlice.map(b => b.runs),
       y: bSlice.map(b => b.batter),
       text: bSlice.map(b => `${num(b.runs)} runs`),
       textposition: "outside",
       marker: { color: bSlice.map(b => b.strike_rate),
                 colorscale: "Plasma", showscale: true,
                 colorbar: { title: { text: "SR", font: { size: 11 } }, thickness: 14, len: 0.75, x: 1.02 } },
       hovertemplate: "<b>%{y}</b><br>Runs: %{x}<br>SR: %{marker.color:.1f}<extra></extra>",
    }],
    { xaxis: { range: [0, bMax * 1.2], automargin: true },
      yaxis: { automargin: true },
      height: 520, margin: { t: 30, r: 100, b: 40, l: bLm } }
  );

  /* ── Top bowlers ── */
  const wSlice = bowlers.slice(0, 12).reverse();
  const wLm    = leftPad(wSlice.map(b => b.bowler));
  const wMax   = Math.max(...wSlice.map(b => Number(b.wickets) || 0), 1);
  plot("bowlerChart",
    [{ type: "bar", orientation: "h",
       x: wSlice.map(b => b.wickets),
       y: wSlice.map(b => b.bowler),
       text: wSlice.map(b => `${num(b.wickets)}W`),
       textposition: "outside",
       marker: { color: wSlice.map(b => b.economy),
                 colorscale: "RdYlGn", reversescale: true, showscale: true,
                 colorbar: { title: { text: "ECO", font: { size: 11 } }, thickness: 14, len: 0.75, x: 1.02 } },
       hovertemplate: "<b>%{y}</b><br>Wickets: %{x}<br>Economy: %{marker.color:.2f}<extra></extra>",
    }],
    { xaxis: { range: [0, wMax * 1.2], automargin: true },
      yaxis: { automargin: true },
      height: 520, margin: { t: 30, r: 100, b: 40, l: wLm } }
  );

  /* ── Toss decision bar ── */
  const tossColors = { bat: "#fbbf24", field: "#2dd4bf" };
  plot("tossDecisionChart",
    [{ type: "bar",
       x: toss.map(r => r.toss_decision || "unknown"),
       y: toss.map(r => r.win_rate),
       text: toss.map(r => pct(r.win_rate)),
       textposition: "outside",
       marker: { color: toss.map(r => tossColors[r.toss_decision] || "#818cf8") },
       customdata: toss.map(r => r.matches),
       hovertemplate: "<b>%{x}</b><br>Win Rate: %{text}<br>Matches: %{customdata}<extra></extra>",
    }],
    { yaxis: { tickformat: ".0%", range: [0, 0.85], automargin: true },
      xaxis: { automargin: true },
      height: 430, margin: { t: 30, r: 30, b: 54, l: 60 } }
  );

  /* ── Toss season line ── */
  const decisions = [...new Set(tossSeason.map(r => r.toss_decision || "unknown"))];
  plot("tossSeasonChart",
    decisions.map(dec => {
      const rows = tossSeason.filter(r => (r.toss_decision || "unknown") === dec);
      return { type: "scatter", mode: "lines+markers", name: dec,
               x: rows.map(r => r.season), y: rows.map(r => r.toss_winner_win_rate),
               line: { color: tossColors[dec] || "#94a3b8", width: 2.5 },
               marker: { color: tossColors[dec] || "#94a3b8", size: 7 },
               hovertemplate: `<b>${escapeHtml(dec)}</b><br>Season: %{x}<br>Win Rate: %{y:.1%}<extra></extra>` };
    }),
    { yaxis: { tickformat: ".0%", range: [0.3, 0.75], automargin: true },
      xaxis: { automargin: true, type: "category" },
      height: 430, margin: { t: 30, r: 24, b: 80, l: 60 } }
  );

  /* ── Venue scatter ── */
  const vSlice = venues.slice(0, 20);
  plot("venueScatter",
    [{ type: "scatter", mode: "markers",
       x: vSlice.map(r => r.avg_first_innings_runs),
       y: vSlice.map(r => r.chasing_win_rate),
       text: vSlice.map(r => r.venue),
       marker: { size: vSlice.map(r => Math.max(14, Math.min(44, (r.matches || 1) * 2.2))),
                 color: vSlice.map(r => r.batting_first_win_rate),
                 colorscale: "RdYlGn", reversescale: true, showscale: true,
                 colorbar: { title: { text: "Bat 1st\nWin%", side: "right", font: { size: 10 } },
                             tickformat: ".0%", thickness: 14, len: 0.75, x: 1.03 },
                 line: { color: "rgba(255,255,255,0.4)", width: 1.5 } },
       hovertemplate: "<b>%{text}</b><br>Avg 1st Innings: %{x:.0f}<br>Chase Win Rate: %{y:.1%}<extra></extra>",
    }],
    { xaxis: { title: { text: "Average First Innings Runs", standoff: 10 }, automargin: true },
      yaxis: { title: { text: "Chasing Win Rate", standoff: 10 }, tickformat: ".0%", automargin: true },
      height: 480, margin: { t: 30, r: 110, b: 80, l: 70 } }
  );

  /* ── Venue runs bar ── */
  const vRuns = venues.slice(0, 16).sort((a, b) => (a.avg_first_innings_runs || 0) - (b.avg_first_innings_runs || 0));
  const vLm   = leftPad(vRuns.map(r => r.venue));
  const vMax  = Math.max(...vRuns.map(r => Number(r.avg_first_innings_runs) || 0), 1);
  plot("venueRunsChart",
    [{ type: "bar", orientation: "h",
       x: vRuns.map(r => r.avg_first_innings_runs),
       y: vRuns.map(r => r.venue),
       text: vRuns.map(r => num(r.avg_first_innings_runs, 1)),
       textposition: "outside",
       marker: { color: vRuns.map(r => r.chasing_win_rate),
                 colorscale: [[0,"#1e3a5f"],[0.5,"#f97316"],[1,"#dc2626"]],
                 showscale: true,
                 colorbar: { title: { text: "Chase\nWin%", font: { size: 10 } },
                             tickformat: ".0%", thickness: 14, len: 0.75, x: 1.03 } },
       customdata: vRuns.map(r => r.chasing_win_rate),
       hovertemplate: "<b>%{y}</b><br>Avg 1st Innings: %{x:.1f}<br>Chase Win Rate: %{customdata:.1%}<extra></extra>",
    }],
    { xaxis: { range: [0, vMax * 1.18], automargin: true },
      yaxis: { automargin: true },
      height: 520, margin: { t: 30, r: 110, b: 40, l: vLm } }
  );
}

// ─── Tables ───────────────────────────────────────────────────────────────────
function renderTables() {
  if (!state.data) return;

  const bs = ($("#batterSearch")?.value  || "").toLowerCase().trim();
  const ws = ($("#bowlerSearch")?.value  || "").toLowerCase().trim();
  const ts = ($("#teamSearch")?.value    || "").toLowerCase().trim();
  const vs = ($("#venueSearch")?.value   || "").toLowerCase().trim();

  const filterBy = (rows, key, term) =>
    !term ? rows : rows.filter(r => String(r[key] ?? "").toLowerCase().includes(term));

  const batters = filterBy(state.data.batters, "batter", bs);
  const bowlers = filterBy(state.data.bowlers, "bowler", ws);
  const teams   = filterBy(state.data.teams,   "team",   ts);
  const venues  = filterBy(state.data.venues,  "venue",  vs);

  table("#teamTable", teams, [
    ["team",               "Team"],
    ["matches",            "Matches",   num],
    ["decisive_matches",   "Decisive",  num],
    ["wins",               "Wins",      num],
    ["losses",             "Losses",    num],
    ["tied_or_no_results", "Tie/NR",    num],
    ["win_rate",           "Win Rate",  pct],
  ]);
  table("#batterTable", batters, [
    ["batter",      "Batter"],
    ["runs",        "Runs",   num],
    ["balls",       "Balls",  num],
    ["fours",       "4s",     num],
    ["sixes",       "6s",     num],
    ["strike_rate", "SR",     v => num(v, 1)],
    ["average",     "Avg",    v => num(v, 1)],
  ]);
  table("#bowlerTable", bowlers, [
    ["bowler",        "Bowler"],
    ["wickets",       "Wickets",  num],
    ["balls",         "Balls",    num],
    ["runs_conceded", "Runs",     num],
    ["economy",       "Economy",  v => num(v, 2)],
    ["average",       "Avg",      v => num(v, 1)],
    ["strike_rate",   "Bowl SR",  v => num(v, 1)],
  ]);
  table("#venueTable", venues, [
    ["venue",                 "Venue"],
    ["matches",               "Matches",      num],
    ["avg_first_innings_runs","Avg 1st Inns", v => num(v, 1)],
    ["batting_first_win_rate","Bat First Win", pct],
    ["chasing_win_rate",      "Chasing Win",  pct],
    ["toss_winner_win_rate",  "Toss Win",     pct],
  ]);
  table("#issueTable", state.data.issues, [
    ["source",  "Source"],
    ["level",   "Level"],
    ["message", "Message"],
  ]);

  // Update issue count badge
  const badge = $("#issueCount");
  if (badge) {
    const n = state.data.issues ? state.data.issues.length : 0;
    badge.textContent = `${n} issue${n !== 1 ? "s" : ""}`;
    badge.classList.toggle("badge-warning", n > 0);
  }
}

function table(selector, rows, cols) {
  const el = $(selector);
  if (!el) return;
  if (!rows || !rows.length) {
    el.innerHTML = "<p class='no-data'>No matching records in this view.</p>";
    return;
  }
  const head = cols.map(([, label]) => `<th>${escapeHtml(label)}</th>`).join("");
  const body = rows.map(row => {
    const wr = Number(row.win_rate);
    const cls = !isNaN(wr) ? (wr > 0.60 ? " class='row-high'" : wr < 0.38 ? " class='row-low'" : "") : "";
    const cells = cols.map(([key, , fmt]) => `<td>${escapeHtml(fmt ? fmt(row[key]) : String(row[key] ?? ""))}</td>`).join("");
    return `<tr${cls}>${cells}</tr>`;
  }).join("");
  el.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

// ─── Chat ─────────────────────────────────────────────────────────────────────
function renderSuggestions() {
  const container = $("#suggestions");
  if (!container) return;
  container.innerHTML = SUGGESTIONS
    .map(q => `<button class="secondary-button suggestion-button" type="button">${escapeHtml(q)}</button>`)
    .join("");
  $$(".suggestion-button").forEach(b =>
    b.addEventListener("click", () => sendChat(b.textContent))
  );
}

function renderChat() {
  const box = $("#chatBox");
  if (!box) return;
  box.innerHTML = state.chat.map(m =>
    `<div class="message ${m.speaker === "user" ? "user" : ""}">
      <strong>${m.speaker === "user" ? "You 👤" : "IPL Bot 🏏"}</strong>
      <span class="message-text">${escapeHtml(m.text).replaceAll("\n", "<br>")}</span>
    </div>`
  ).join("");
  box.scrollTop = box.scrollHeight;
}

async function sendChat(forced) {
  const inp = $("#chatInput");
  const q   = forced || inp.value.trim();
  if (!q) return;
  state.chat.push({ speaker: "user", text: q });
  if (inp) inp.value = "";
  renderChat();

  // Show typing indicator
  state.chat.push({ speaker: "bot", text: "Thinking… ⏳" });
  renderChat();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, seasons: ["All"], teams: state.filters.teams, venues: state.filters.venues }),
    }).then(r => r.json());
    state.chat.pop(); // remove typing indicator
    state.chat.push({ speaker: "bot", text: res.answer });
  } catch {
    state.chat.pop();
    state.chat.push({ speaker: "bot", text: "Sorry, couldn't reach the server. Please try again! 🔄" });
  }
  renderChat();
}

// ─── Scroll reveal ────────────────────────────────────────────────────────────
let _revealObserver = null;

function initScrollReveal() {
  // Auto-tag structural elements that aren't yet marked
  $$(".panel:not(.reveal), .explain-card:not(.reveal), .page-banner:not(.reveal)").forEach(el => {
    el.classList.add("reveal");
  });

  if (!_revealObserver) {
    _revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add("visible");
          _revealObserver.unobserve(e.target);
        }
      });
    }, { threshold: 0.07, rootMargin: "0px 0px -24px 0px" });
  }

  // Observe all reveal/stagger elements not yet visible
  $$(".reveal:not(.visible), .stagger-children:not(.visible)").forEach(el => {
    _revealObserver.observe(el);
  });
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────
init().catch(err => {
  console.error(err);
  document.body.innerHTML =
    `<main style="padding:2rem;font-family:sans-serif;color:#f8fafc;background:#0f172a">
      <h1 style="color:#ef4444">Dashboard failed to load 😢</h1>
      <p>Make sure the server is running: <code>uvicorn app:app --reload</code></p>
      <pre style="background:#1e293b;padding:1rem;border-radius:8px">${escapeHtml(err.message)}</pre>
    </main>`;
});
