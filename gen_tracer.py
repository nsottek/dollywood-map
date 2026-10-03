import pypdfium2 as pdfium
from PIL import Image
import base64, io, os, json

PROJECT = os.path.dirname(os.path.abspath(__file__))

# Render at 1.5x — 918×645, lighter file; JS will output coords ×2 for 1836×1290 space
pdf = pdfium.PdfDocument('/Users/natesottek/Downloads/DW26_GENERAL_ParkMap_20260824.pdf')
bitmap = pdf[0].render(scale=1.5)
pil = bitmap.to_pil()
map_img = pil.crop((0, 0, pil.width, 645))
buf = io.BytesIO()
map_img.save(buf, format='JPEG', quality=85, optimize=True)
raw = buf.getvalue()
img_b64 = base64.b64encode(raw).decode()
img_src = f'data:image/jpeg;base64,{img_b64}'
print(f'Tracer map: {len(raw):,} bytes  b64: {len(img_b64):,} chars')

ZONES = [
    ('showstreet',  'Showstreet',                   '#1E88E5'),
    ('timber',      'Timber Canyon',                '#795548'),
    ('wildpass',    'Wilderness Pass',              '#00897B'),
    ('craftsman',   "Craftsman's Valley",           '#43A047'),
    ('owens',       'Owens Farm',                   '#F57C00'),
    ('village',     'The Village',                  '#5E35B1'),
    ('countryfair', 'Country Fair',                 '#E91E63'),
    ('rivertown',   'Rivertown Junction',           '#C62828'),
    ('jukebox',     'Jukebox Junction',             '#E64A19'),
    ('dolly',       'The Dolly Parton Experience',  '#8E24AA'),
    ('wildwood',    'Wildwood Grove',               '#2E7D32'),
]

zone_options = '\n'.join(
    f'<option value="{k}">{n}</option>' for k,n,c in ZONES
)
zones_init = json.dumps({k: {'name': n, 'color': c, 'pts': []} for k,n,c in ZONES})

html = f'''<title>Dollywood Zone Tracer</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg:#0d1117;--surface:#161b22;--surface2:#21262d;
  --border:rgba(255,255,255,.1);--txt:#c9d1d9;--txt2:#8b949e;
  --accent:#f5b731;--ff:\'DM Sans\',system-ui,sans-serif;
  --mono:\'JetBrains Mono\',monospace;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;background:var(--bg);color:var(--txt);font-family:var(--ff);font-size:14px;overflow:hidden}}
/* ── Header ── */
#hdr{{
  display:flex;align-items:center;gap:10px;
  padding:10px 14px;
  background:var(--surface);
  border-bottom:1px solid var(--border);
  flex-shrink:0;flex-wrap:wrap;
}}
#hdr h1{{font-size:15px;font-weight:600;color:var(--accent);white-space:nowrap;margin-right:4px}}
.z-dot{{width:12px;height:12px;border-radius:3px;flex-shrink:0}}
#zone-sel{{
  background:var(--surface2);color:var(--txt);
  border:1px solid var(--border);border-radius:6px;
  padding:5px 8px;font-family:var(--ff);font-size:13px;
  cursor:pointer;flex-shrink:0;
}}
.btn{{
  background:var(--surface2);color:var(--txt);
  border:1px solid var(--border);border-radius:6px;
  padding:5px 12px;font-family:var(--ff);font-size:13px;
  cursor:pointer;white-space:nowrap;
  transition:background .15s,border-color .15s;
}}
.btn:hover{{background:#30363d;border-color:#6e7681}}
.btn.primary{{background:#238636;border-color:#2ea043;color:#fff}}
.btn.primary:hover{{background:#2ea043}}
.btn.danger{{background:#5a1a1a;border-color:#da3633;color:#f85149}}
.btn.danger:hover{{background:#6a2020}}
#pt-count{{font-size:12px;color:var(--txt2);white-space:nowrap;margin-left:auto}}
/* ── Map area ── */
#mc{{
  flex:1;overflow:hidden;position:relative;
  cursor:crosshair;user-select:none;
  background:#050a10;
}}
#mc.grabbing{{cursor:grabbing}}
#mi{{
  position:absolute;top:0;left:0;
  transform-origin:0 0;will-change:transform;
}}
#mi img{{display:block;width:918px;height:645px}}
#msvg{{
  position:absolute;top:0;left:0;
  width:918px;height:645px;
  pointer-events:none;
  overflow:visible;
}}
/* ── Output bar ── */
#out-bar{{
  display:flex;align-items:center;gap:8px;
  padding:8px 14px;
  background:var(--surface);
  border-top:1px solid var(--border);
  flex-shrink:0;
}}
#out-bar label{{font-size:12px;color:var(--txt2);white-space:nowrap}}
#out-txt{{
  flex:1;background:var(--bg);color:#7ee787;
  border:1px solid var(--border);border-radius:6px;
  padding:6px 10px;font-family:var(--mono);font-size:11px;
  resize:none;height:44px;
}}
/* ── App shell ── */
#app{{display:flex;flex-direction:column;height:100%}}
/* ── Instructions overlay ── */
#tip{{
  position:absolute;top:12px;left:50%;transform:translateX(-50%);
  background:rgba(13,17,23,.85);backdrop-filter:blur(6px);
  border:1px solid var(--border);border-radius:8px;
  padding:8px 16px;font-size:12px;color:var(--txt2);
  pointer-events:none;white-space:nowrap;z-index:10;
  transition:opacity .3s;
}}
</style>

<div id="app">
  <div id="hdr">
    <h1>Zone Tracer</h1>
    <div class="z-dot" id="z-dot"></div>
    <select id="zone-sel">{zone_options}</select>
    <button class="btn" id="btn-undo">↩ Undo</button>
    <button class="btn danger" id="btn-clear">Clear</button>
    <button class="btn primary" id="btn-close">Close Polygon</button>
    <span id="pt-count">0 pts</span>
  </div>

  <div id="mc">
    <div id="mi">
      <img id="mimg" src="{img_src}" draggable="false">
      <svg id="msvg" viewBox="0 0 918 645" xmlns="http://www.w3.org/2000/svg"></svg>
    </div>
    <div id="tip">Click to place points · Two-finger or scroll to zoom · Drag to pan</div>
  </div>

  <div id="out-bar">
    <label>Output (1836×1290):</label>
    <textarea id="out-txt" readonly spellcheck="false"></textarea>
    <button class="btn primary" id="btn-copy">Copy JSON</button>
    <button class="btn" id="btn-load">Load saved</button>
    <button class="btn danger" id="btn-reset">Reset all</button>
  </div>
</div>

<script>
const ZONES = {zones_init};
let zoneKey = Object.keys(ZONES)[0];
const mc = document.getElementById('mc');
const mi = document.getElementById('mi');
const msvg = document.getElementById('msvg');

// ── Load from localStorage ──────────────────────────────────────────────────
try {{
  const saved = localStorage.getItem('dw-tracer-zones');
  if (saved) Object.assign(ZONES, JSON.parse(saved));
}} catch(e) {{}}

function save() {{
  try {{ localStorage.setItem('dw-tracer-zones', JSON.stringify(ZONES)); }} catch(e) {{}}
}}

// ── Zone selector ───────────────────────────────────────────────────────────
const zSel = document.getElementById('zone-sel');
const zDot = document.getElementById('z-dot');
function setZone(k) {{
  zoneKey = k;
  zDot.style.background = ZONES[k].color;
  updatePtCount();
  redraw();
}}
zSel.addEventListener('change', e => setZone(e.target.value));
setZone(zoneKey);

// ── Pan / zoom ──────────────────────────────────────────────────────────────
let s=1, tx=0, ty=0, dragged=false;
let t0=[], pd=0, pm=null, mdown=false, lm=null;

function apply(ani) {{
  mi.style.transition = ani ? 'transform .35s cubic-bezier(.32,.72,0,1)' : 'none';
  mi.style.transform = `translate(${{tx}}px,${{ty}}px) scale(${{s}})`;
}}
function clamp() {{
  const cw=mc.clientWidth, ch=mc.clientHeight;
  const iw=918*s, ih=645*s;
  if(iw<=cw) tx=(cw-iw)/2; else tx=Math.min(0,Math.max(cw-iw,tx));
  if(ih<=ch) ty=(ch-ih)/2; else ty=Math.min(0,Math.max(ch-ih,ty));
  apply(false);
}}
function dst(t) {{ const dx=t[0].clientX-t[1].clientX,dy=t[0].clientY-t[1].clientY; return Math.sqrt(dx*dx+dy*dy); }}
function mid(t) {{ return {{x:(t[0].clientX+t[1].clientX)/2, y:(t[0].clientY+t[1].clientY)/2}}; }}

mc.addEventListener('touchstart', e=>{{
  e.preventDefault(); dragged=false;
  t0=Array.from(e.touches);
  if(t0.length===2){{pd=dst(t0);pm=mid(t0);}}
}},{{passive:false}});
mc.addEventListener('touchmove', e=>{{
  e.preventDefault(); const t=Array.from(e.touches); dragged=true;
  if(t.length===2){{
    const d=dst(t),m=mid(t),r=d/pd;
    const rect=mc.getBoundingClientRect();
    const cx=m.x-rect.left,cy=m.y-rect.top;
    const ns=Math.min(8,Math.max(1,s*r)),sr=ns/s;
    tx=cx-sr*(cx-tx); ty=cy-sr*(cy-ty); s=ns;
    if(pm){{tx+=m.x-pm.x;ty+=m.y-pm.y;}}
    pd=d; pm=m;
  }} else if(t.length===1&&t0.length===1){{
    tx+=t[0].clientX-t0[0].clientX; ty+=t[0].clientY-t0[0].clientY; t0=t;
  }}
  apply(false);
}},{{passive:false}});
mc.addEventListener('touchend', e=>{{ t0=Array.from(e.touches); if(!t0.length)clamp(); }});
mc.addEventListener('mousedown', e=>{{ if(e.button!==0)return; mdown=true; lm={{x:e.clientX,y:e.clientY}}; dragged=false; mc.classList.add('grabbing'); }});
window.addEventListener('mousemove', e=>{{
  if(!mdown)return;
  const dx=e.clientX-lm.x, dy=e.clientY-lm.y;
  if(Math.abs(dx)+Math.abs(dy)>4)dragged=true;
  tx+=dx; ty+=dy; lm={{x:e.clientX,y:e.clientY}}; apply(false);
}});
window.addEventListener('mouseup', ()=>{{ if(mdown){{mdown=false;mc.classList.remove('grabbing');clamp();}} }});
mc.addEventListener('wheel', e=>{{
  e.preventDefault();
  const r=mc.getBoundingClientRect();
  const cx=e.clientX-r.left, cy=e.clientY-r.top;
  const d=e.deltaY>0?.88:1.14;
  const ns=Math.min(8,Math.max(1,s*d)), sr=ns/s;
  tx=cx-sr*(cx-tx); ty=cy-sr*(cy-ty); s=ns; apply(false);
}},{{passive:false}});

// ── Click → add point ───────────────────────────────────────────────────────
mc.addEventListener('click', e=>{{
  if(dragged) return;
  const rect=mc.getBoundingClientRect();
  // CSS coords within mi container (918×645 space)
  const cx = (e.clientX-rect.left-tx)/s;
  const cy = (e.clientY-rect.top-ty)/s;
  // Clamp to image bounds
  if(cx<0||cy<0||cx>918||cy>645) return;
  const svgX = Math.round(cx);
  const svgY = Math.round(cy);
  ZONES[zoneKey].pts.push([svgX, svgY]);
  save(); updatePtCount(); redraw(); updateOutput();
  hideTip();
}});

function hideTip() {{
  const tip=document.getElementById('tip');
  if(tip) tip.style.opacity='0';
}}

// ── Controls ────────────────────────────────────────────────────────────────
document.getElementById('btn-undo').addEventListener('click', ()=>{{
  ZONES[zoneKey].pts.pop(); save(); updatePtCount(); redraw(); updateOutput();
}});
document.getElementById('btn-clear').addEventListener('click', ()=>{{
  if(!confirm(`Clear all points for ${{ZONES[zoneKey].name}}?`)) return;
  ZONES[zoneKey].pts = []; save(); updatePtCount(); redraw(); updateOutput();
}});
document.getElementById('btn-close').addEventListener('click', ()=>{{
  const pts = ZONES[zoneKey].pts;
  if(pts.length>=3) {{
    pts.push([...pts[0]]); save(); updatePtCount(); redraw(); updateOutput();
  }}
}});
document.getElementById('btn-copy').addEventListener('click', ()=>{{
  const txt = document.getElementById('out-txt').value;
  navigator.clipboard.writeText(txt).catch(()=>{{
    document.getElementById('out-txt').select();
    document.execCommand('copy');
  }});
  const btn = document.getElementById('btn-copy');
  btn.textContent='Copied!'; setTimeout(()=>btn.textContent='Copy JSON',1500);
}});
document.getElementById('btn-load').addEventListener('click', ()=>{{
  try {{
    const saved=localStorage.getItem('dw-tracer-zones');
    if(saved) Object.assign(ZONES, JSON.parse(saved));
    redraw(); updateOutput(); updatePtCount();
    alert('Loaded from browser storage.');
  }} catch(e) {{ alert('Nothing saved yet.'); }}
}});
document.getElementById('btn-reset').addEventListener('click', ()=>{{
  if(!confirm('Reset ALL zone points? This cannot be undone.')) return;
  Object.values(ZONES).forEach(z=>z.pts=[]);
  localStorage.removeItem('dw-tracer-zones');
  redraw(); updateOutput(); updatePtCount();
}});

function updatePtCount() {{
  const n=ZONES[zoneKey].pts.length;
  document.getElementById('pt-count').textContent=`${{n}} pt${{n===1?'':'s'}}`;
}}

// ── Redraw SVG ──────────────────────────────────────────────────────────────
function redraw() {{
  msvg.innerHTML='';
  Object.entries(ZONES).forEach(([k,z])=>{{
    if(!z.pts.length) return;
    const isActive = k===zoneKey;
    const opacity = isActive ? 0.55 : 0.25;
    const sw = isActive ? 2.5 : 1.5;

    if(z.pts.length>=2) {{
      const poly=document.createElementNS('http://www.w3.org/2000/svg','polygon');
      poly.setAttribute('points', z.pts.map(p=>p.join(',')).join(' '));
      poly.setAttribute('fill', z.color);
      poly.setAttribute('fill-opacity', isActive?'0.25':'0.12');
      poly.setAttribute('stroke', z.color);
      poly.setAttribute('stroke-width', sw);
      poly.setAttribute('stroke-opacity', opacity);
      poly.setAttribute('stroke-linejoin','round');
      msvg.appendChild(poly);
    }}

    // Vertex dots
    z.pts.forEach((p,i)=>{{
      const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
      c.setAttribute('cx',p[0]); c.setAttribute('cy',p[1]);
      c.setAttribute('r', isActive?(i===0?5:3):2);
      c.setAttribute('fill', i===0?'#fff':z.color);
      c.setAttribute('stroke', z.color);
      c.setAttribute('stroke-width','1.5');
      c.setAttribute('fill-opacity', isActive?'1':'0.6');
      msvg.appendChild(c);
    }});

    // Label on active zone
    if(isActive && z.pts.length) {{
      const cx=z.pts.reduce((a,p)=>a+p[0],0)/z.pts.length;
      const cy=z.pts.reduce((a,p)=>a+p[1],0)/z.pts.length;
      const t=document.createElementNS('http://www.w3.org/2000/svg','text');
      t.setAttribute('x',cx); t.setAttribute('y',cy);
      t.setAttribute('text-anchor','middle');
      t.setAttribute('dominant-baseline','middle');
      t.setAttribute('font-size','11');
      t.setAttribute('font-family','DM Sans,sans-serif');
      t.setAttribute('font-weight','600');
      t.setAttribute('fill','#fff');
      t.setAttribute('paint-order','stroke');
      t.setAttribute('stroke','#000');
      t.setAttribute('stroke-width','3');
      t.setAttribute('stroke-linejoin','round');
      t.textContent=z.name;
      msvg.appendChild(t);
    }}
  }});
}}

// ── Output JSON ──────────────────────────────────────────────────────────────
// Coords are stored in 918×645 space; output ×2 → 1836×1290 for the main app
function updateOutput() {{
  const out={{}};
  Object.entries(ZONES).forEach(([k,z])=>{{
    if(z.pts.length>=3) {{
      out[k]=z.pts.map(p=>`${{p[0]*2}},${{p[1]*2}}`).join(' ');
    }}
  }});
  document.getElementById('out-txt').value = JSON.stringify(out, null, 2);
}}

// ── Init ────────────────────────────────────────────────────────────────────
redraw();
updateOutput();
// Center map in view
const initFit = mc.clientWidth/918;
s=Math.max(1,Math.min(1.5,initFit));
tx=(mc.clientWidth-918*s)/2;
ty=(mc.clientHeight-645*s)/2;
apply(false);
</script>'''

out = os.path.join(PROJECT, 'tracer.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Written: {out}  ({os.path.getsize(out):,} bytes)')
