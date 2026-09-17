#!/usr/bin/env python3
"""
Stage 4 — render a self-contained dashboard from enriched.json.

    python3 build_dashboard.py --enriched output/enriched.json \
        --meta output/run-meta.json --out output/creator-pool.html \
        --title "Creator Pool" --platform instagram --niche "skincare"

Output is one HTML file with all data inlined: no network calls, no CDN, so it
satisfies the Artifact CSP and keeps working offline. Publish it with the
Artifact tool.

Design notes (keep these if you restyle): engagement rate is the hero metric,
the mean/median toggle exists because a 12-post mean is dominated by one viral
reel, and provenance chips are shown because a creator found by more than one
search method is a stronger signal than one found once.
"""
import argparse, json, os, sys

CSS = """
:root{
  --ink:#10171A; --paper:#ECEFEB;
  --bg:var(--paper); --surface:#F7F8F5; --line:#CBD2CC; --line-soft:#DDE2DC;
  --text:#10171A; --text-dim:#5A6660; --text-faint:#8B948E;
  --accent:#0E6E63; --accent-soft:#D3E5E1; --accent-ink:#0A4F47;
  --warn:#9A6314; --warn-bg:#F4E7D2;
  --src-profile:#9A5236; --src-profile-bg:#F0E2DA;
  --src-hashtag:#3A5F92; --src-hashtag-bg:#DCE4EF;
  --src-reels:#6B4E8E; --src-reels-bg:#E5DEEE;
  --shadow:0 1px 2px rgba(16,23,26,.06); --r:2px;
  --display:"Avenir Next Condensed","Avenir Next",ui-sans-serif,system-ui,sans-serif;
  --body:"Avenir Next","Segoe UI",system-ui,-apple-system,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:var(--ink); --surface:#182125; --line:#2E3B40; --line-soft:#242F34;
    --text:#E4E9E5; --text-dim:#96A29C; --text-faint:#6B7873;
    --accent:#45C9B8; --accent-soft:#123833; --accent-ink:#8FE3D6;
    --warn:#E0B267; --warn-bg:#34291A;
    --src-profile:#D89873; --src-profile-bg:#33241C;
    --src-hashtag:#8FB0DC; --src-hashtag-bg:#1B2735;
    --src-reels:#B69BD6; --src-reels-bg:#261D33;
    --shadow:0 1px 2px rgba(0,0,0,.3);
  }
}
:root[data-theme="dark"]{
  --bg:var(--ink); --surface:#182125; --line:#2E3B40; --line-soft:#242F34;
  --text:#E4E9E5; --text-dim:#96A29C; --text-faint:#6B7873;
  --accent:#45C9B8; --accent-soft:#123833; --accent-ink:#8FE3D6;
  --warn:#E0B267; --warn-bg:#34291A;
  --src-profile:#D89873; --src-profile-bg:#33241C;
  --src-hashtag:#8FB0DC; --src-hashtag-bg:#1B2735;
  --src-reels:#B69BD6; --src-reels-bg:#261D33;
  --shadow:0 1px 2px rgba(0,0,0,.3);
}
:root[data-theme="light"]{
  --bg:var(--paper); --surface:#F7F8F5; --line:#CBD2CC; --line-soft:#DDE2DC;
  --text:#10171A; --text-dim:#5A6660; --text-faint:#8B948E;
  --accent:#0E6E63; --accent-soft:#D3E5E1; --accent-ink:#0A4F47;
  --warn:#9A6314; --warn-bg:#F4E7D2;
  --src-profile:#9A5236; --src-profile-bg:#F0E2DA;
  --src-hashtag:#3A5F92; --src-hashtag-bg:#DCE4EF;
  --src-reels:#6B4E8E; --src-reels-bg:#E5DEEE;
  --shadow:0 1px 2px rgba(16,23,26,.06);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--body);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:32px 24px 72px}
.masthead{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;flex-wrap:wrap;border-bottom:2px solid var(--text);padding-bottom:14px}
.eyebrow{font-family:var(--display);text-transform:uppercase;letter-spacing:.14em;font-size:11px;color:var(--text-dim);margin:0 0 4px}
h1{font-family:var(--display);font-weight:600;font-size:clamp(28px,4.5vw,42px);letter-spacing:-.01em;margin:0;text-wrap:balance;line-height:1.05}
.masthead-meta{display:flex;align-items:center;gap:18px}
.count-big{font-family:var(--mono);font-size:34px;font-variant-numeric:tabular-nums;line-height:1}
.count-big span{font-family:var(--display);font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--text-dim);display:block;margin-top:5px}
.theme-btn{font-family:var(--display);text-transform:uppercase;letter-spacing:.1em;font-size:10px;background:transparent;color:var(--text-dim);border:1px solid var(--line);border-radius:var(--r);padding:7px 10px;cursor:pointer}
.theme-btn:hover{color:var(--accent);border-color:var(--accent)}
.summary{display:grid;grid-template-columns:1.3fr 1fr;gap:28px;padding:22px 0;border-bottom:1px solid var(--line-soft)}
@media (max-width:820px){.summary{grid-template-columns:1fr;gap:22px}}
.panel-label{font-family:var(--display);text-transform:uppercase;letter-spacing:.14em;font-size:10px;color:var(--text-faint);margin:0 0 10px;display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.bandbar{display:flex;height:26px;border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.bandbar div+div{border-left:1px solid var(--bg)}
.bandkey{display:flex;flex-wrap:wrap;gap:4px 16px;margin-top:10px}
.bandkey button{display:flex;align-items:center;gap:7px;background:none;border:none;padding:2px 0;cursor:pointer;color:var(--text-dim);font-family:var(--body);font-size:12px}
.bandkey button:hover{color:var(--text)}
.bandkey button[aria-pressed="false"]{opacity:.38}
.swatch{width:10px;height:10px;border-radius:1px;flex:none}
.bandkey b{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:500;color:var(--text)}
.health{display:flex;flex-direction:column;gap:9px;font-size:13px}
.hrow{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:baseline;color:var(--text-dim)}
.hrow b{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:500;color:var(--text)}
.hrow .dot{width:8px;height:8px;border-radius:50%;align-self:center}
.hnote{font-size:11.5px;color:var(--text-faint);line-height:1.5;margin:2px 0 0}
.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:16px 0;border-bottom:1px solid var(--line-soft);position:sticky;top:0;background:var(--bg);z-index:5}
.search{position:relative;flex:1 1 220px;min-width:180px}
.search input{width:100%;font-family:var(--body);font-size:14px;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:9px 12px 9px 30px}
.search input::placeholder{color:var(--text-faint)}
.search svg{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--text-faint)}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{font-family:var(--display);text-transform:uppercase;letter-spacing:.09em;font-size:10px;background:var(--surface);color:var(--text-dim);border:1px solid var(--line);border-radius:var(--r);padding:7px 10px;cursor:pointer}
.chip:hover{color:var(--text)}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.toggle{display:flex;border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.toggle button{font-family:var(--display);text-transform:uppercase;letter-spacing:.09em;font-size:10px;background:var(--surface);color:var(--text-dim);border:none;padding:7px 11px;cursor:pointer}
.toggle button[aria-pressed="true"]{background:var(--accent);color:var(--bg)}
select{font-family:var(--body);font-size:13px;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:8px 10px}
.resultline{display:flex;justify-content:space-between;align-items:baseline;gap:16px;padding:14px 0 4px;font-size:12px;color:var(--text-dim);flex-wrap:wrap}
.resultline b{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:500;color:var(--text)}
.linkbtn{background:none;border:none;padding:0;font:inherit;color:var(--accent);cursor:pointer;text-decoration:underline}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px;margin-top:14px}
.card{display:flex;flex-direction:column;gap:10px;background:var(--surface);border:1px solid var(--line-soft);border-radius:var(--r);padding:14px 15px;box-shadow:var(--shadow);transition:border-color .12s}
@media (prefers-reduced-motion:reduce){.card{transition:none}}
.card:hover{border-color:var(--accent)}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.handle{font-family:var(--mono);font-size:14px;font-weight:500;color:var(--text);text-decoration:none;word-break:break-all;line-height:1.35}
.handle:hover{color:var(--accent);text-decoration:underline}
.handle::before{content:"@";color:var(--text-faint)}
.followers{text-align:right;flex:none}
.followers b{display:block;font-family:var(--mono);font-size:15px;font-weight:500;font-variant-numeric:tabular-nums;line-height:1.15}
.followers span{font-family:var(--display);text-transform:uppercase;letter-spacing:.1em;font-size:9px;color:var(--text-faint)}
.metrics{display:grid;grid-template-columns:auto 1fr;gap:12px;align-items:center;padding:9px 0;border-top:1px solid var(--line-soft);border-bottom:1px solid var(--line-soft)}
.er{display:flex;align-items:baseline;gap:5px}
.er b{font-family:var(--mono);font-size:22px;font-weight:500;font-variant-numeric:tabular-nums;line-height:1}
.er i{font-style:normal;font-family:var(--display);text-transform:uppercase;letter-spacing:.1em;font-size:9px;color:var(--text-faint)}
.subm{display:flex;flex-wrap:wrap;gap:3px 14px;font-size:11.5px;color:var(--text-dim)}
.subm span{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--text)}
.bio{font-size:12.5px;line-height:1.5;color:var(--text-dim);margin:0;white-space:pre-line;overflow-wrap:anywhere}
.cardfoot{display:flex;flex-wrap:wrap;gap:5px;align-items:center;padding-top:3px}
.src{font-size:10.5px;padding:3px 7px;border-radius:var(--r);border:1px solid transparent;white-space:nowrap}
.src-profile_search{color:var(--src-profile);background:var(--src-profile-bg);border-color:var(--src-profile-bg)}
.src-hashtag{color:var(--src-hashtag);background:var(--src-hashtag-bg);border-color:var(--src-hashtag-bg)}
.src-reels{color:var(--src-reels);background:var(--src-reels-bg);border-color:var(--src-reels-bg)}
.tag{font-family:var(--display);text-transform:uppercase;letter-spacing:.1em;font-size:9px;border-radius:var(--r);padding:3px 6px;white-space:nowrap}
.tag-cross{color:var(--accent-ink);background:var(--accent-soft);border:1px solid var(--accent)}
.tag-skew{color:var(--warn);background:var(--warn-bg);border:1px solid var(--warn)}
.tag-agency{color:var(--warn);background:var(--warn-bg);border:1px solid var(--warn)}
.recency{font-family:var(--mono);font-size:11px;font-variant-numeric:tabular-nums;color:var(--text-faint);margin-right:auto}
.recency.fresh{color:var(--accent)}
.contact{border-top:1px dashed var(--line);padding-top:9px;margin-top:auto;display:flex;flex-direction:column;gap:5px}
.contact-label{font-family:var(--display);text-transform:uppercase;letter-spacing:.12em;font-size:9px;color:var(--text-faint);display:flex;gap:6px;align-items:center}
.contact-row{display:flex;gap:5px 10px;flex-wrap:wrap;align-items:baseline;font-size:11.5px}
.contact a{color:var(--accent);text-decoration:none;overflow-wrap:anywhere}
.contact a:hover{text-decoration:underline}
.cmail{font-family:var(--mono);font-size:11.5px;font-weight:500}
.cmeta{color:var(--text-faint)}
.cnone{color:var(--text-faint);font-style:italic;font-size:11.5px}
.empty{padding:56px 0;text-align:center;color:var(--text-dim)}
.foot{margin-top:34px;padding-top:16px;border-top:1px solid var(--line-soft);font-size:12px;color:var(--text-faint);line-height:1.7}
.foot b{color:var(--text-dim);font-weight:600}
.foot code{font-family:var(--mono);font-size:11px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
"""

JS = r"""
const POOL = __DATA__;
const META = __META__;

const BANDS = [
  {k:'b0', label:'Under 1%',  lo:0,   hi:1,        c:'#CFDEDA', d:'#1C4842'},
  {k:'b1', label:'1-3%',      lo:1,   hi:3,        c:'#9AC8BF', d:'#2C6B62'},
  {k:'b2', label:'3-6%',      lo:3,   hi:6,        c:'#5AA396', d:'#3E9083'},
  {k:'b3', label:'6%+',       lo:6,   hi:Infinity, c:'#15564E', d:'#6FD2C2'},
  {k:'bx', label:'No like data', lo:null, hi:null,  c:'#C4C9C4', d:'#3A4650'}
];
const METHODS = [
  {k:'profile_search', label:'Profile search', varName:'--src-profile'},
  {k:'hashtag',        label:'Hashtag',        varName:'--src-hashtag'},
  {k:'reels',          label:'Reels',          varName:'--src-reels'}
];
const state = {q:'', bands:new Set(), methods:new Set(), cross:false, clean:false,
               email:false, metric:'mean', sort:'er-desc'};

const erOf   = r => state.metric === 'views' ? r.engagement_rate_on_views
                  : state.metric === 'mean' ? r.engagement_rate : r.engagement_rate_median;
const likeOf = r => state.metric === 'median' ? r.median_likes : r.avg_likes;
const cmtOf  = r => state.metric === 'median' ? r.median_comments : r.avg_comments;
const bandOf = r => {
  const v = erOf(r);
  if (v === null || v === undefined) return 'bx';
  return BANDS.find(b => b.lo !== null && v >= b.lo && v < b.hi).k;
};
const fmt = n => n >= 1e6 ? (n/1e6).toFixed(n>=1e7?0:2).replace(/\.?0+$/,'')+'M'
               : n >= 1e3 ? (n/1e3).toFixed(n>=1e5?0:1).replace(/\.0$/,'')+'K'
               : String(Math.round(n));
const methodOf = s => s.split(':')[0];
const queryOf  = s => s.split(':').slice(1).join(':');
function esc(s){ return String(s).replace(/[&<>"']/g, m =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
function host(u){ try { return new URL(u).hostname.replace(/^www\./,''); } catch(e){ return u; } }

POOL.forEach(r => {
  r.methods = [...new Set((r.sources||[]).map(methodOf))];
  r._hay = (r.handle + ' ' + (r.bio||'') + ' ' + (r.sources||[]).join(' ') + ' ' +
            ((r.contact && r.contact.emails) ? r.contact.emails.join(' ') : '')).toLowerCase();
  r._skewed = (r.top_post_vs_median || 0) >= 5;
});

function isDark(){
  const a = document.documentElement.getAttribute('data-theme');
  return a ? a === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
}
const bandColor = b => isDark() ? b.d : b.c;

function paintSummary(){
  const counts = {};
  BANDS.forEach(b => counts[b.k] = POOL.filter(r => bandOf(r) === b.k).length);
  document.getElementById('bandbar').innerHTML = BANDS.filter(b => counts[b.k] > 0)
    .map(b => `<div style="flex:${counts[b.k]};background:${bandColor(b)}" title="${b.label}: ${counts[b.k]}"></div>`).join('');
  document.getElementById('bandkey').innerHTML = BANDS.map(b =>
    `<button type="button" data-band="${b.k}" aria-pressed="${state.bands.size===0||state.bands.has(b.k)}">
       <span class="swatch" style="background:${bandColor(b)}"></span>${b.label} <b>${counts[b.k]}</b>
     </button>`).join('');
  document.getElementById('metriclabel').textContent =
    state.metric === 'views' ? 'against views' : state.metric === 'mean' ? 'by mean (of followers)' : 'by median (of followers)';
}

function visible(){
  let rows = POOL.filter(r =>
    (!state.q || r._hay.includes(state.q)) &&
    (state.bands.size === 0 || state.bands.has(bandOf(r))) &&
    (state.methods.size === 0 || r.methods.some(m => state.methods.has(m))) &&
    (!state.cross || r.methods.length > 1) &&
    (!state.clean || !r._skewed) &&
    (!state.email || !!(r.contact && r.contact.emails.length))
  );
  const nn = v => (v === null || v === undefined) ? -1 : v;
  const cmp = {
    'er-desc':        (a,b) => nn(erOf(b)) - nn(erOf(a)),
    'er-asc':         (a,b) => nn(erOf(a)) - nn(erOf(b)),
    'followers-desc': (a,b) => b.follower_count - a.follower_count,
    'followers-asc':  (a,b) => a.follower_count - b.follower_count,
    'likes-desc':     (a,b) => nn(likeOf(b)) - nn(likeOf(a)),
    'recent-desc':    (a,b) => a.days_since_last_post - b.days_since_last_post,
    'handle-asc':     (a,b) => a.handle.localeCompare(b.handle)
  }[state.sort];
  return rows.sort(cmp);
}

function contactBlock(r){
  const c = r.contact;
  if (!c) return `<div class="contact"><span class="contact-label">Contact</span>
      <span class="cnone">Not researched — outside the contact scope</span></div>`;
  const bits = [];
  c.emails.forEach((e,i) => {
    const ag = (c.agency_email||[]).indexOf(e);
    const name = ag > -1 ? (c.agency_names||[])[ag] : null;
    bits.push(`<span><a class="cmail" href="mailto:${esc(e)}">${esc(e)}</a>${
      name ? ` <span class="tag tag-agency">${esc(name)}</span>` : ''}</span>`);
  });
  if (c.booking) bits.push(`<span class="cmeta">book <a href="${esc(c.booking)}" target="_blank" rel="noopener noreferrer">${esc(host(c.booking))}</a></span>`);
  if (c.business_contact) bits.push(`<span class="cmeta">partnerships <a href="${esc(c.business_contact)}" target="_blank" rel="noopener noreferrer">${esc(c.business_contact_label||host(c.business_contact))}</a></span>`);
  if (c.website) bits.push(`<span class="cmeta">site <a href="${esc(c.website)}" target="_blank" rel="noopener noreferrer">${esc(host(c.website))}</a></span>`);
  const lib = c.linkinbio ? `<span class="cmeta">· ${esc(c.linkinbio.service)} resolved, ${c.linkinbio.link_count} links</span>` : '';
  return `<div class="contact"><span class="contact-label">Contact${lib}</span>
    ${bits.length ? `<div class="contact-row">${bits.join('')}</div>`
                  : `<span class="cnone">No public contact path found</span>`}</div>`;
}

function render(){
  const rows = visible();
  document.getElementById('shown').textContent = rows.length;
  const withEr = rows.filter(r => erOf(r) !== null && erOf(r) !== undefined);
  document.getElementById('typical').textContent = withEr.length
    ? (() => { const s = withEr.map(erOf).sort((a,b)=>a-b); const m = s.length>>1;
               return (s.length%2 ? s[m] : (s[m-1]+s[m])/2).toFixed(2)+'%'; })() : '—';

  document.getElementById('grid').innerHTML = rows.length ? rows.map(r => {
    const er = erOf(r), l = likeOf(r), c = cmtOf(r);
    const alt = state.metric === 'views' ? r.engagement_rate
              : state.metric === 'mean' ? r.engagement_rate_median : r.engagement_rate;
    const altLabel = state.metric === 'views' ? 'of followers'
                   : state.metric === 'mean' ? 'median' : 'mean';
    const chips = (r.sources||[]).map(s => {
      const m = methodOf(s);
      const lab = m === 'profile_search' ? 'search' : m === 'hashtag' ? '#' : 'reel';
      return `<span class="src src-${m}">${lab} · ${esc(queryOf(s))}</span>`;
    }).join('');
    return `<article class="card">
      <div class="card-top">
        <a class="handle" href="${esc(r.profile_url)}" target="_blank" rel="noopener noreferrer">${esc(r.handle)}</a>
        <div class="followers"><b>${fmt(r.follower_count)}</b><span>followers</span></div>
      </div>
      <div class="metrics">
        <div class="er"><b>${er===null||er===undefined?'—':er.toFixed(2)+'%'}</b><i>eng. rate</i></div>
        <div class="subm">
          <div>likes <span>${l===null||l===undefined?'—':fmt(l)}</span></div>
          <div>comments <span>${c===null||c===undefined?'—':fmt(c)}</span></div>
          <div>${altLabel} <span>${alt===null||alt===undefined?'—':alt.toFixed(2)+'%'}</span></div>
        </div>
      </div>
      <p class="bio">${esc(r.bio||'')}</p>
      <div class="cardfoot">
        <span class="recency${r.days_since_last_post<=7?' fresh':''}">${r.days_since_last_post}d ago · ${r.last_post_date}</span>
        ${r._skewed ? `<span class="tag tag-skew">top post ${r.top_post_vs_median}×</span>` : ''}
        ${r.methods.length>1 ? `<span class="tag tag-cross">${r.methods.length} methods</span>` : ''}
      </div>
      <div class="cardfoot">${chips}</div>
      ${contactBlock(r)}
    </article>`;
  }).join('') : `<div class="empty" style="grid-column:1/-1">No creators match those filters.
      <button class="linkbtn" type="button" id="clearall">Clear all filters</button></div>`;
  const cl = document.getElementById('clearall');
  if (cl) cl.onclick = clearAll;
}

function clearAll(){
  state.q=''; state.bands.clear(); state.methods.clear();
  state.cross=false; state.clean=false; state.email=false;
  document.getElementById('q').value='';
  syncChips(); paintSummary(); render();
}
function syncChips(){
  document.querySelectorAll('[data-method]').forEach(b =>
    b.setAttribute('aria-pressed', state.methods.size===0 || state.methods.has(b.dataset.method)));
  document.getElementById('crossbtn').setAttribute('aria-pressed', state.cross);
  document.getElementById('cleanbtn').setAttribute('aria-pressed', state.clean);
  document.getElementById('emailbtn').setAttribute('aria-pressed', state.email);
  document.querySelectorAll('[data-metric]').forEach(b =>
    b.setAttribute('aria-pressed', b.dataset.metric === state.metric));
}

(function health(){
  const stale = META.stale||[], un = META.unavailable||[], oor = META.out_of_range||[];
  let html = `<div class="hrow"><span class="dot" style="background:var(--accent)"></span>
       <span>Ranked below</span><b>${POOL.length}</b></div>`;
  if (oor.length) html += `<div class="hrow"><span class="dot" style="background:var(--text-faint)"></span>
       <span>Outside follower range</span><b>${oor.length}</b></div>`;
  if (stale.length) html += `<div class="hrow"><span class="dot" style="background:var(--warn)"></span>
       <span>Dropped, silent ${META.max_age_days}+ days</span><b>${stale.length}</b></div>
     <p class="hnote">${stale.map(s => esc(s[0])+' ('+s[1]+'d)').join(' · ')}</p>`;
  if (un.length) html += `<div class="hrow"><span class="dot" style="background:var(--text-faint)"></span>
       <span>No data — API could not return posts</span><b>${un.length}</b></div>
     <p class="hnote">${un.map(esc).join(' · ')}</p>`;
  if (META.truncated_by_limit) html += `<div class="hrow"><span class="dot" style="background:var(--text-faint)"></span>
       <span>Below the requested cut-off</span><b>${META.truncated_by_limit}</b></div>`;
  document.getElementById('health').innerHTML = html;
})();

document.getElementById('q').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); render(); });
document.getElementById('sort').addEventListener('change', e => { state.sort = e.target.value; render(); });
document.getElementById('bandkey').addEventListener('click', e => {
  const b = e.target.closest('[data-band]'); if (!b) return;
  const k = b.dataset.band;
  state.bands.has(k) ? state.bands.delete(k) : state.bands.add(k);
  if (state.bands.size === BANDS.length) state.bands.clear();
  paintSummary(); render();
});
document.querySelectorAll('[data-method]').forEach(b => b.addEventListener('click', () => {
  const k = b.dataset.method;
  state.methods.has(k) ? state.methods.delete(k) : state.methods.add(k);
  if (state.methods.size === METHODS.length) state.methods.clear();
  syncChips(); render();
}));
document.getElementById('crossbtn').addEventListener('click', () => { state.cross=!state.cross; syncChips(); render(); });
document.getElementById('cleanbtn').addEventListener('click', () => { state.clean=!state.clean; syncChips(); render(); });
document.getElementById('emailbtn').addEventListener('click', () => { state.email=!state.email; syncChips(); render(); });
document.querySelectorAll('[data-metric]').forEach(b => b.addEventListener('click', () => {
  state.metric = b.dataset.metric; state.bands.clear(); syncChips(); paintSummary(); render();
}));
document.getElementById('themebtn').addEventListener('click', () => {
  document.documentElement.setAttribute('data-theme', isDark() ? 'light' : 'dark');
  paintSummary(); render();
});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (!document.documentElement.getAttribute('data-theme')) { paintSummary(); render(); }
});
paintSummary(); syncChips(); render();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enriched", required=True)
    ap.add_argument("--meta")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Creator Pool")
    ap.add_argument("--platform", default="instagram")
    ap.add_argument("--niche", default="")
    ap.add_argument("--captured", default="")
    args = ap.parse_args()

    with open(args.enriched) as fh:
        rows = json.load(fh)
    meta = {}
    if args.meta and os.path.exists(args.meta):
        with open(args.meta) as fh:
            meta = json.load(fh)

    skewed = [r for r in rows if (r.get("top_post_vs_median") or 0) >= 5]
    nulls = [r for r in rows if r.get("engagement_rate") is None]
    hidden = [r for r in rows if r.get("likes_hidden_posts")]
    pinned = [r for r in rows if r.get("pinned_in_sample")]
    worst = max(skewed, key=lambda r: r["top_post_vs_median"]) if skewed else None
    rng = meta.get("follower_range") or [0, None]
    rng_txt = f"{rng[0]:,}–{rng[1]:,}" if rng[1] else f"{rng[0]:,}+"
    has_views = any(r.get("engagement_rate_on_views") is not None for r in rows)
    views_btn = '<button type="button" data-metric="views" aria-pressed="false">Views</button>' if has_views else ""

    eyebrow = " · ".join(x for x in [args.platform, args.niche, "ranked by engagement"] if x)
    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    metajson = json.dumps(meta, ensure_ascii=False).replace("</", "<\\/")

    caveats = []
    if skewed:
        caveats.append(
            f"<b>Switch to Median</b> to see typical performance: one viral post can dominate a "
            f"12-post mean, and {len(skewed)} of {len(rows)} creators here have a top post at least "
            f"5× their median — the <code>top post N×</code> tag marks them."
            + (f" <b>{worst['handle']}</b> reads {worst['engagement_rate']}% on the mean and "
               f"{worst['engagement_rate_median']}% on the median." if worst else ""))
    if hidden or nulls:
        caveats.append(
            f"{len(hidden)} creators hide like counts on some posts, where the preview count was used"
            + (f"; {len(nulls)} hide them on all 12, so no rate is computable" if nulls else "") + ".")
    if pinned:
        caveats.append(
            f"Pinned posts appear in {len(pinned)} creators' samples and sit outside chronological "
            f"order, so recency is taken from the newest post, not the first in the grid.")

    body = f"""
<div class="wrap">
  <header class="masthead">
    <div><p class="eyebrow">{eyebrow}</p><h1>{args.title}</h1></div>
    <div class="masthead-meta">
      <div class="count-big">{len(rows)}<span>creators</span></div>
      <button class="theme-btn" id="themebtn" type="button">Theme</button>
    </div>
  </header>
  <section class="summary">
    <div>
      <p class="panel-label"><span>Engagement rate <span id="metriclabel">by mean</span> — click a band to filter</span></p>
      <div class="bandbar" id="bandbar"></div>
      <div class="bandkey" id="bandkey"></div>
    </div>
    <div>
      <p class="panel-label">Pool health — {meta.get('sourced', len(rows))} sourced · {rng_txt} followers</p>
      <div class="health" id="health"></div>
    </div>
  </section>
  <div class="controls">
    <label class="search">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
        <circle cx="7" cy="7" r="4.5"></circle><path d="M10.5 10.5 14 14"></path></svg>
      <input id="q" type="search" placeholder="Search handles, bios, terms, emails…" aria-label="Search creators">
    </label>
    <div class="toggle" role="group" aria-label="Metric basis">
      <button type="button" data-metric="mean" aria-pressed="true">Mean</button>
      <button type="button" data-metric="median" aria-pressed="false">Median</button>
      {views_btn}
    </div>
    <div class="chips">
      <button class="chip" type="button" data-method="profile_search">Profile search</button>
      <button class="chip" type="button" data-method="hashtag">Hashtag</button>
      <button class="chip" type="button" data-method="reels">Reels</button>
      <button class="chip" type="button" id="crossbtn" aria-pressed="false">Found 2+ ways</button>
      <button class="chip" type="button" id="cleanbtn" aria-pressed="false">Hide viral spikes</button>
      <button class="chip" type="button" id="emailbtn" aria-pressed="false">Has email</button>
    </div>
    <select id="sort" aria-label="Sort creators">
      <option value="er-desc">Engagement, high → low</option>
      <option value="er-asc">Engagement, low → high</option>
      <option value="followers-desc">Followers, high → low</option>
      <option value="followers-asc">Followers, low → high</option>
      <option value="likes-desc">Likes per post</option>
      <option value="recent-desc">Most recently posted</option>
      <option value="handle-asc">Handle, A → Z</option>
    </select>
  </div>
  <div class="resultline">
    <span>Showing <b id="shown">{len(rows)}</b> of <b>{len(rows)}</b> creators</span>
    <span>Typical engagement in view <b id="typical">—</b></span>
  </div>
  <main class="grid" id="grid"></main>
  <footer class="foot">
    <b>Engagement rate = (avg likes + avg comments) ÷ followers</b>, over each creator's last 12 posts.
    {' '.join(caveats)}<br>
    {'Captured ' + args.captured + '. ' if args.captured else ''}This pool is ranked by engagement but
    not filtered for brand fit — brands and off-topic accounts matched on caption text may remain.
  </footer>
</div>
"""

    doc = (f"<title>{args.title}</title>\n"
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           f"<style>{CSS}</style>\n{body}\n"
           f"<script>{JS.replace('__DATA__', payload).replace('__META__', metajson)}</script>\n")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(doc)
    print(f"wrote {args.out} ({len(doc):,} bytes, {len(rows)} creators)")


if __name__ == "__main__":
    sys.exit(main())
