import pypdfium2 as pdfium
from PIL import Image
import base64, io, os, json

PROJECT = os.path.dirname(os.path.abspath(__file__))

# ── Build park data from JSON ─────────────────────────────────────────────────
with open(os.path.join(PROJECT, 'dollywood_attractions.json')) as _f:
    _pd = json.load(_f)

AREA_META = [
    ('showstreet',  'Showstreet',                     '#1E88E5', 981,  1015),
    ('timber',      'Timber Canyon',                  '#795548', 702,   560),
    ('wildpass',    'Wilderness Pass',                '#00897B', 1009,  276),
    ('craftsman',   "Craftsman's Valley",             '#43A047', 1207,  426),
    ('owens',       'Owens Farm',                     '#F57C00', 1156,  711),
    ('village',     'The Village',                    '#5E35B1', 1637,  976),
    ('countryfair', 'Country Fair',                   '#E91E63', 1670, 1134),
    ('rivertown',   'Rivertown Junction',             '#C62828', 1294,  998),
    ('jukebox',     'Jukebox Junction',               '#E64A19', 1243, 1172),
    ('dolly',       'The Dolly Parton Experience',    '#8E24AA', 1014, 1137),
    ('wildwood',    'Wildwood Grove',                 '#2E7D32', 466,   462),
]
AREA_KEY = {
    'Showstreet': 'showstreet', 'Timber Canyon': 'timber',
    'Wilderness Pass': 'wildpass', "Craftsman's Valley": 'craftsman',
    'Owens Farm': 'owens', 'The Village': 'village',
    'Country Fair': 'countryfair', 'Rivertown Junction': 'rivertown',
    'Jukebox Junction': 'jukebox', 'Dolly Parton Experience': 'dolly',
    'The Dolly Parton Experience': 'dolly', 'Wildwood Grove': 'wildwood',
}

def _js_item(it, iid):
    p = [f'id:{iid}', f'name:{json.dumps(it["name"])}']
    if it.get('type'):          p.append(f'type:{json.dumps(it["type"])}')
    if it.get('heightMin'):     p.append(f'hmin:{it["heightMin"]}')
    if it.get('heightMax'):     p.append(f'hmax:{it["heightMax"]}')
    if it.get('timeSaver'):
        p.append(f'ts:{2 if it.get("timeSaverType")=="premium" else 1}')
    if it.get('temporarilyClosed'): p.append('closed:1')
    if it.get('seasonal'):
        p.append('seasonal:1')
        if it.get('seasonDates'): p.append(f'sdates:{json.dumps(it["seasonDates"])}')
    if it.get('venue') and it['venue'] != it.get('name'):
        p.append(f'venue:{json.dumps(it["venue"])}')
    if it.get('description'):
        p.append(f'desc:{json.dumps(it["description"])}')
    return '{' + ','.join(p) + '}'

_uid = -1
_area_att = {k: [] for k,*_ in AREA_META}
_area_din = {k: [] for k,*_ in AREA_META}
_area_shp = {k: [] for k,*_ in AREA_META}
_att_seen = {k: set() for k,*_ in AREA_META}

for _it in _pd.get('rides', []) + _pd.get('entertainment', []):
    _key = AREA_KEY.get(_it.get('area', ''))
    if not _key: continue
    _mid = _it.get('mapId')
    if _mid is not None and _mid in _att_seen[_key]: continue
    if _mid is not None: _att_seen[_key].add(_mid); _iid = _mid
    else: _uid -= 1; _iid = _uid
    _area_att[_key].append(_js_item(_it, _iid))

for _it in _pd.get('dining', []):
    _key = AREA_KEY.get(_it.get('area', ''))
    if not _key: continue
    _mid = _it.get('mapId')
    _iid = _mid if _mid is not None else (_uid := _uid - 1)
    _area_din[_key].append(_js_item(_it, _iid))

_shops_seen = {_it.get('mapId') for _it in _pd.get('shops', []) if _it.get('mapId') is not None}
_shp_items = list(_pd.get('shops', []))
for _it in _pd.get('crafts', []):
    if _it.get('mapId') not in _shops_seen: _shp_items.append(_it)
_shp_seen_per = {k: set() for k,*_ in AREA_META}
for _it in _shp_items:
    _key = AREA_KEY.get(_it.get('area', ''))
    if not _key: continue
    _mid = _it.get('mapId')
    if _mid is not None and _mid in _shp_seen_per[_key]: continue
    if _mid is not None: _shp_seen_per[_key].add(_mid); _iid = _mid
    else: _uid -= 1; _iid = _uid
    _area_shp[_key].append(_js_item(_it, _iid))

def _arr(items): return '[' + ','.join(items) + ']' if items else '[]'
_parts = []
for _k, _nm, _col, _cx, _cy in AREA_META:
    _parts.append(
        f' {_k}:{{name:{json.dumps(_nm)},color:{json.dumps(_col)},cx:{_cx},cy:{_cy},'
        f'att:{_arr(_area_att[_k])},din:{_arr(_area_din[_k])},shp:{_arr(_area_shp[_k])}}}'
    )
park_js = '{' + ','.join(_parts) + '}'

# ── Render & encode map image ─────────────────────────────────────────────────
# Render at 4x for higher-resolution detail (2448×1720 map area)
SCALE = 4.0
pdf4 = pdfium.PdfDocument(os.path.join(PROJECT, 'DW26_GENERAL_ParkMap_20260824.pdf'))
bitmap4 = pdf4[0].render(scale=SCALE)
pil4 = bitmap4.to_pil()
CROP_H = round(1290 * SCALE / 3.0)  # proportional to original 3x crop
map_img = pil4.crop((0, 0, pil4.width, CROP_H))  # 2448×1720 — map only, no listings
print(f'Map image size: {map_img.width}×{map_img.height}')
buf = io.BytesIO()
map_img.save(buf, format='JPEG', quality=90, optimize=True)
raw = buf.getvalue()
img_b64 = base64.b64encode(raw).decode()
img_src = f'data:image/jpeg;base64,{img_b64}'
print(f'Map JPEG: {len(raw):,} bytes  b64: {len(img_b64):,} chars')

# ── HTML (no DOCTYPE/html/head/body — Artifact skeleton provides them) ────────
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Dollywood 2026 Guide</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap">
<style>
/* Layout: full-screen app — dark header / map / slide-up panel or list */
:root {{
  --bg:#fdf6ec;--surface:#fffdf8;--surface2:#f5ead6;--border:rgba(60,30,10,.12);
  --txt:#1c0e00;--txt2:#5a3a1a;--txt3:#9a7550;
  --header:#180c00;--red:#ce1126;--gold:#f5b731;
  --sans:'DM Sans',system-ui,sans-serif;--serif:'DM Serif Display',Georgia,serif;
  /* Area overlay colours — fixed, intentionally vivid */
  --c-showstreet:#1E88E5;--c-timber:#795548;--c-wildpass:#00897B;
  --c-craftsman:#43A047;--c-owens:#F57C00;--c-village:#5E35B1;
  --c-fair:#E91E63;--c-rivertown:#C62828;--c-jukebox:#E64A19;
  --c-dolly:#8E24AA;--c-wildwood:#2E7D32;
}}
@media(prefers-color-scheme:dark){{
  :root:not([data-theme=light]){{
    --bg:#100800;--surface:#1e0f03;--surface2:#2c1a08;--border:rgba(255,220,160,.12);
    --txt:#fff3e0;--txt2:#d4a870;--txt3:#7a6040;
    color-scheme:dark;
  }}
}}
:root[data-theme=dark]{{
  --bg:#100800;--surface:#1e0f03;--surface2:#2c1a08;--border:rgba(255,220,160,.12);
  --txt:#fff3e0;--txt2:#d4a870;--txt3:#7a6040;
  color-scheme:dark;
}}
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
html,body{{height:100%;overflow:hidden;font-family:var(--sans);background:var(--bg);color:var(--txt)}}
#app{{height:100%;display:flex;flex-direction:column}}

/* ── Header ─────────────────────────────────────────────────────────────── */
#hdr{{
  flex:0 0 auto;background:var(--header);
  padding:10px 16px 10px;
  padding-top:max(10px,env(safe-area-inset-top,0px));
  display:flex;align-items:center;gap:12px;
  border-bottom:1px solid rgba(245,183,49,.2);
}}
#hdr-logo{{flex:1;min-width:0}}
#hdr-title{{font-family:var(--serif);font-size:19px;color:#fff;line-height:1;margin-bottom:1px}}
#hdr-sub{{font-size:10px;font-weight:600;letter-spacing:.1em;color:var(--gold);text-transform:uppercase}}
#toggle{{display:flex;background:rgba(255,255,255,.1);border-radius:8px;padding:3px;gap:2px;flex-shrink:0}}
.tbtn{{border:none;background:transparent;color:rgba(255,255,255,.55);font-size:13px;font-weight:600;
  padding:6px 16px;border-radius:6px;cursor:pointer;font-family:var(--sans);transition:all .2s}}
.tbtn.on{{background:var(--red);color:#fff}}

/* ── View shells ─────────────────────────────────────────────────────────── */
.view{{flex:1;overflow:hidden;display:none;position:relative;flex-direction:column}}
.view.on{{display:flex}}

/* ── Map container ───────────────────────────────────────────────────────── */
#mc{{flex:1;overflow:hidden;position:relative;touch-action:none;cursor:grab}}
#mc.grab{{cursor:grabbing}}
#mi{{position:absolute;top:0;left:0;transform-origin:0 0;will-change:transform}}
#mi img{{display:block;width:100%;height:auto;pointer-events:none;user-select:none;-webkit-user-drag:none}}
#msvg{{position:absolute;top:0;left:0;width:100%;height:100%;overflow:visible}}
#msvg polygon{{cursor:pointer;stroke-width:2;stroke-opacity:.85;transition:fill-opacity .18s,stroke-width .18s}}

/* ── Slide-up panel ──────────────────────────────────────────────────────── */
#panel{{
  position:absolute;bottom:0;left:0;right:0;
  background:var(--surface);
  border-radius:20px 20px 0 0;
  box-shadow:0 -6px 32px rgba(0,0,0,.22);
  transform:translateY(105%);
  transition:transform .38s cubic-bezier(.32,.72,0,1);
  z-index:50;display:flex;flex-direction:column;
  height:50vh;overflow:hidden;
}}
#panel.on{{transform:translateY(0)}}
@media(min-width:768px){{
  #panel{{height:auto;max-height:38vh}}
}}
.ph-bar{{flex:0 0 auto;display:flex;justify-content:center;padding:10px;cursor:pointer}}
.ph-nub{{width:36px;height:4px;border-radius:2px;background:var(--border)}}
.ph{{flex:0 0 auto;padding:0 14px 10px;display:flex;align-items:center;gap:8px}}
#p-back{{border:none;background:none;color:var(--red);font-size:22px;cursor:pointer;
  padding:2px 6px 2px 0;display:none;line-height:1;font-family:var(--sans)}}
#p-back.on{{display:block}}
.p-dot{{width:13px;height:13px;border-radius:4px;flex-shrink:0}}
#p-title{{font-family:var(--serif);font-size:17px;color:var(--txt);flex:1;min-width:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
#p-close{{border:none;background:var(--surface2);color:var(--txt2);font-size:17px;
  width:28px;height:28px;border-radius:50%;cursor:pointer;line-height:1;flex-shrink:0;
  font-family:var(--sans)}}
#pbody{{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;position:relative}}

/* ── Category sections ───────────────────────────────────────────────────── */
.cs{{padding:0 14px 14px}}
@media(min-width:768px){{
  #pbody>.cs-wrap{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0 8px;padding:0 14px 14px}}
  #pbody>.cs-wrap .cs{{padding:0}}
}}
.cl{{font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  color:var(--txt3);padding:8px 0 5px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:5px;margin-bottom:2px}}
.cl-ic{{width:18px;height:18px;border-radius:4px;font-size:11px;
  display:flex;align-items:center;justify-content:center}}
.att-ic{{background:#e3f2fd;color:#1565c0}}
.din-ic{{background:#e8f5e9;color:#2e7d32}}
.shp-ic{{background:#fff8e1;color:#e65100}}
@media(prefers-color-scheme:dark){{
  :root:not([data-theme=light]) .att-ic{{background:#0d2340;color:#90caf9}}
  :root:not([data-theme=light]) .din-ic{{background:#0d2318;color:#a5d6a7}}
  :root:not([data-theme=light]) .shp-ic{{background:#2a1a00;color:#ffcc80}}
}}
:root[data-theme=dark] .att-ic{{background:#0d2340;color:#90caf9}}
:root[data-theme=dark] .din-ic{{background:#0d2318;color:#a5d6a7}}
:root[data-theme=dark] .shp-ic{{background:#2a1a00;color:#ffcc80}}
.ir{{display:flex;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);
  gap:7px;cursor:pointer;user-select:none}}
.ir:last-child{{border-bottom:none}}
.ir:active{{background:var(--surface2);margin:0 -4px;padding-left:4px;padding-right:4px;border-radius:6px}}
.in{{font-size:11px;font-weight:700;color:var(--txt3);min-width:20px}}
.iname{{flex:1;font-size:13.5px;color:var(--txt);line-height:1.3}}
.itags{{display:flex;gap:3px;flex-shrink:0}}
.tag{{font-size:10px;font-weight:700;padding:1px 5px;border-radius:4px}}
.h-tag{{background:#fff3e0;color:#bf360c}}
.ts-tag{{background:#ede7f6;color:#4527a0}}
.ts-prem{{background:#f3e5f5;color:#6a1b9a}}
.cl-tag{{background:#ffebee;color:#b71c1c}}
.sea-tag{{background:#e8f5e9;color:#1b5e20}}
.d-tag{{background:#fce4ec;color:#880e4f}}
@media(prefers-color-scheme:dark){{
  :root:not([data-theme=light]) .h-tag{{background:#2a1500;color:#ffcc80}}
  :root:not([data-theme=light]) .ts-tag{{background:#2a1a00;color:#f5b731}}
  :root:not([data-theme=light]) .ts-prem{{background:#3a1000;color:#ff8c42}}
  :root:not([data-theme=light]) .cl-tag{{background:#2a0000;color:#ff8a80}}
  :root:not([data-theme=light]) .sea-tag{{background:#002a10;color:#69f0ae}}
  :root:not([data-theme=light]) .d-tag{{background:#2a0a00;color:#ffab76}}
}}
:root[data-theme=dark] .h-tag{{background:#2a1500;color:#ffcc80}}
:root[data-theme=dark] .ts-tag{{background:#2a1a00;color:#f5b731}}
:root[data-theme=dark] .ts-prem{{background:#3a1000;color:#ff8c42}}
:root[data-theme=dark] .cl-tag{{background:#2a0000;color:#ff8a80}}
:root[data-theme=dark] .sea-tag{{background:#002a10;color:#69f0ae}}
:root[data-theme=dark] .d-tag{{background:#2a0a00;color:#ffab76}}
.iarr{{color:var(--txt3);font-size:16px}}

/* ── Item detail (within panel) ──────────────────────────────────────────── */
#idet{{position:absolute;inset:0;background:var(--surface);
  transform:translateY(100%);transition:transform .28s cubic-bezier(.32,.72,0,1);z-index:5;
  overflow-y:auto;-webkit-overflow-scrolling:touch;border-radius:inherit}}
#idet.on{{transform:translateY(0)}}
.det-body{{padding:16px 16px 32px}}
.det-area-pill{{display:inline-flex;align-items:center;gap:6px;
  background:var(--surface2);border-radius:20px;padding:4px 10px;margin-bottom:14px}}
.det-area-dot{{width:10px;height:10px;border-radius:3px}}
.det-area-nm{{font-size:11px;font-weight:600;color:var(--txt2)}}
.det-name{{font-family:var(--serif);font-size:22px;color:var(--txt);line-height:1.2;margin-bottom:6px;text-wrap:balance}}
.det-id{{font-size:12px;color:var(--txt3);margin-bottom:14px}}
.det-tags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:18px}}
.det-tag{{font-size:12px;font-weight:600;padding:4px 10px;border-radius:6px}}
.det-att{{background:#e3f2fd;color:#1565c0}}
.det-din{{background:#e8f5e9;color:#2e7d32}}
.det-shp{{background:#fff8e1;color:#e65100}}
.det-h{{background:#fff3e0;color:#bf360c}}
.det-ts{{background:#ede7f6;color:#4527a0}}
.det-tsprem{{background:#f3e5f5;color:#6a1b9a}}
.det-closed{{background:#ffebee;color:#b71c1c;font-weight:700}}
.det-sea{{background:#e8f5e9;color:#1b5e20}}
.det-type{{background:var(--surface2);color:var(--txt2)}}
.det-dol{{background:#fce4ec;color:#880e4f}}
.det-info{{background:var(--surface2);border-radius:12px;padding:14px 16px;font-size:14px;color:var(--txt2);line-height:1.65}}

/* ── List view ───────────────────────────────────────────────────────────── */
#list-hdr{{flex:0 0 auto;background:var(--surface);
  border-bottom:1px solid var(--border);padding:10px 16px;display:flex;flex-direction:column;gap:8px}}
.frow{{display:flex;gap:8px;align-items:center;overflow-x:auto;-webkit-overflow-scrolling:touch;
  scrollbar-width:none;padding-bottom:2px}}
.frow::-webkit-scrollbar{{display:none}}
.fsel{{
  flex-shrink:0;padding:7px 30px 7px 12px;
  border:1.5px solid var(--border);border-radius:20px;
  font-size:13px;font-family:var(--sans);font-weight:500;
  color:var(--txt);background:var(--surface2);
  appearance:none;-webkit-appearance:none;cursor:pointer;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
}}
.chip{{
  flex-shrink:0;padding:7px 14px;border-radius:20px;
  font-size:13px;font-weight:500;border:1.5px solid var(--border);
  background:var(--surface2);color:var(--txt2);cursor:pointer;white-space:nowrap;
  transition:background .15s,border-color .15s,color .15s;
}}
.chip.on{{background:var(--red);border-color:var(--red);color:#fff}}
.chip.ts-on{{background:#b07800;border-color:#b07800;color:#fff}}
#list-body{{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:0 16px 16px}}
.area-badge{{display:flex;align-items:center;gap:8px;padding:18px 0 8px;
  font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--txt2)}}
.area-badge-dot{{width:10px;height:10px;border-radius:3px;flex-shrink:0}}
@media(min-width:768px){{
  #list-body .cs-wrap{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:0 24px;align-items:start}}
  #list-body .cs-wrap .cs{{padding:0 0 16px}}
}}
.list-empty{{text-align:center;color:var(--txt3);padding:52px 16px;font-size:15px}}
/* List detail full-screen overlay */
#ldet{{
  position:fixed;inset:0;z-index:200;
  background:var(--surface);
  transform:translateY(100%);transition:transform .32s cubic-bezier(.32,.72,0,1);
  display:flex;flex-direction:column;border-radius:20px 20px 0 0;
  padding-bottom:env(safe-area-inset-bottom,0px);
}}
#ldet.on{{transform:translateY(0)}}
.ldet-hdr{{flex:0 0 auto;padding:12px 16px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:8px;background:var(--surface)}}
#ldet-inner{{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:0 0 24px}}
.back-btn{{border:none;background:none;color:var(--red);font-size:15px;font-weight:600;
  cursor:pointer;display:flex;align-items:center;gap:3px;font-family:var(--sans);padding:4px 0}}
</style>
</head>
<body>
<!-- ── App shell ─────────────────────────────────────────────────────────── -->
<div id="app">

  <header id="hdr">
    <div id="hdr-logo">
      <div id="hdr-title">Dollywood</div>
      <div id="hdr-sub">2026 Park Guide</div>
    </div>
    <div id="toggle">
      <button class="tbtn on" onclick="switchView('map')">Map</button>
      <button class="tbtn"    onclick="switchView('list')">List</button>
    </div>
  </header>

  <!-- MAP VIEW -->
  <div id="map-view" class="view on">
    <div id="mc">
      <div id="mi">
        <img src="{img_src}" alt="Dollywood 2026 Park Map" width="{map_img.width}" height="{map_img.height}">
        <svg id="msvg" viewBox="0 0 1836 1290" preserveAspectRatio="none">
          <polygon data-area="showstreet"  fill="var(--c-showstreet)" fill-opacity=".3" stroke="var(--c-showstreet)" points="746,1022 756,950 840,904 996,894 1146,872 1204,932 1158,954 1140,990 1170,1024 1166,1052 1048,1060 986,1054 908,1068 908,1092 922,1158 818,1124 758,1104"/>
          <polygon data-area="timber"      fill="var(--c-timber)"     fill-opacity=".3" stroke="var(--c-timber)"     points="732,834 780,730 818,588 866,460 894,408 816,322 748,338 748,420 776,464 776,514 730,552 690,554 642,536 530,518 512,566 504,640 506,658 586,722 688,816"/>
          <polygon data-area="wildpass"    fill="var(--c-wildpass)"   fill-opacity=".3" stroke="var(--c-wildpass)"   points="896,392 822,306 816,236 868,172 912,116 948,32 1008,6 1128,8 1180,56 1196,146 1136,140 1120,188 1122,228 1146,288 1146,376 1090,430 976,468 948,646 880,666 844,612"/>
          <polygon data-area="craftsman"   fill="var(--c-craftsman)"  fill-opacity=".3" stroke="var(--c-craftsman)"  points="1184,42 1234,22 1278,90 1320,116 1276,236 1284,314 1326,384 1306,494 1384,718 1396,850 1332,842 1244,810 1236,694 1204,662 1168,578 1064,634 1002,606 976,524 1002,464 1144,416 1162,372 1158,280 1130,184 1154,152 1206,154"/>
          <polygon data-area="owens"       fill="var(--c-owens)"      fill-opacity=".3" stroke="var(--c-owens)"      points="1234,692 1246,816 1174,820 1110,790 1080,714 1054,652 1110,628 1188,634 1210,650"/>
          <polygon data-area="village"     fill="var(--c-village)"    fill-opacity=".3" stroke="var(--c-village)"    points="1446,938 1462,980 1482,1004 1556,1012 1610,1010 1662,1022 1736,1026 1796,1022 1810,988 1818,902 1720,898 1544,910"/>
          <polygon data-area="countryfair" fill="var(--c-fair)"       fill-opacity=".3" stroke="var(--c-fair)"       points="1502,1024 1512,1092 1542,1162 1588,1198 1620,1214 1638,1256 1784,1256 1780,1212 1762,1182 1786,1128 1794,1070 1788,1036 1678,1028 1600,1016"/>
          <polygon data-area="rivertown"   fill="var(--c-rivertown)"  fill-opacity=".3" stroke="var(--c-rivertown)"  points="1318,858 1208,842 1156,862 1214,928 1164,956 1154,982 1162,1008 1178,1044 1262,1076 1304,1102 1366,1128 1424,1134 1492,1128 1474,1034 1444,974 1388,910"/>
          <polygon data-area="jukebox"     fill="var(--c-jukebox)"    fill-opacity=".3" stroke="var(--c-jukebox)"    points="1276,1104 1190,1062 1106,1066 1106,1096 1070,1114 1066,1156 1118,1168 1128,1190 1132,1258 1166,1288 1272,1284 1368,1280 1404,1234 1460,1196 1476,1146 1422,1138 1368,1136"/>
          <polygon data-area="dolly"       fill="var(--c-dolly)"      fill-opacity=".3" stroke="var(--c-dolly)"      points="1094,1068 1092,1090 1062,1108 1056,1160 1082,1170 1118,1192 1112,1222 906,1226 910,1170 944,1148 912,1102 934,1074 962,1052"/>
          <polygon data-area="wildwood"    fill="var(--c-wildwood)"   fill-opacity=".3" stroke="var(--c-wildwood)"   points="762,466 768,508 738,538 702,544 654,530 616,524 566,518 546,510 524,512 514,530 498,594 454,646 410,668 358,680 336,670 210,600 26,540 2,388 28,338 94,308 164,306 248,334 252,448 342,440 390,402 446,356 500,306 550,310 574,340 652,346 704,348 744,352 746,392 738,426"/>
        </svg>
      </div>
    </div>

    <!-- Slide-up panel -->
    <div id="panel">
      <div class="ph-bar" onclick="closePanel()"><div class="ph-nub"></div></div>
      <div class="ph">
        <button id="p-back" onclick="panelBack()">←</button>
        <div class="p-dot" id="p-dot"></div>
        <div id="p-title"></div>
        <button id="p-close" onclick="closePanel()">×</button>
      </div>
      <div id="pbody">
        <!-- item detail overlay sits inside pbody -->
        <div id="idet">
          <div class="det-body" id="idet-body"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- LIST VIEW -->
  <div id="list-view" class="view">
    <div id="list-hdr">
      <div class="frow">
        <select id="f-area" class="fsel">
          <option value="">All areas</option>
          <option value="showstreet">Showstreet</option>
          <option value="timber">Timber Canyon</option>
          <option value="wildpass">Wilderness Pass</option>
          <option value="craftsman">Craftsman's Valley</option>
          <option value="owens">Owens Farm</option>
          <option value="village">The Village</option>
          <option value="countryfair">Country Fair</option>
          <option value="rivertown">Rivertown Junction</option>
          <option value="jukebox">Jukebox Junction</option>
          <option value="dolly">The Dolly Parton Experience</option>
          <option value="wildwood">Wildwood Grove</option>
        </select>
        <select id="f-height" class="fsel">
          <option value="0">Any height</option>
          <option value="-1">36 in. max</option>
          <option value="36">36 in</option>
          <option value="39">39 in</option>
          <option value="42">42 in</option>
          <option value="48">48 in</option>
          <option value="50">50 in</option>
          <option value="55">55 in</option>
        </select>
      </div>
      <div class="frow">
        <button class="chip on" data-cat="all">All</button>
        <button class="chip" data-cat="rides">Rides</button>
        <button class="chip" data-cat="shows">Shows</button>
        <button class="chip" data-cat="din">Dining</button>
        <button class="chip" data-cat="shp">Shopping</button>
        <button class="chip" id="f-ts">TimeSaver</button>
      </div>
    </div>
    <div id="list-body"></div>
    <!-- Full-screen item detail for list view -->
    <div id="ldet">
      <div class="ldet-hdr">
        <button class="back-btn" onclick="closeLdet()">← Back</button>
      </div>
      <div id="ldet-inner"></div>
    </div>
  </div>

</div><!-- #app -->

<script>
// ── Park data ────────────────────────────────────────────────────────────────
const TYPE_LABELS={{
  roller_coaster:'Roller Coaster',family:'Family Ride',water:'Water Ride',
  thrill:'Thrill Ride',pre_k:'Pre-K Ride',attraction:'Attraction',
  show:'Live Show',venue:'Theater',film:'Film',
  interactive_experience:'Experience',character_meet:'Character Meet',
  dance_party:'Event',music:'Live Music',restaurant:'Restaurant',
  cafe:'Café',bakery:'Bakery',snack:'Snack',bbq:'BBQ',
  pizza:'Pizza',beverage:'Beverages',ice_cream:'Ice Cream',
  food_hall:'Food Hall',american:'American',event_space:'Event Space',
  clothing:'Clothing',gifts:'Gifts',souvenirs:'Souvenirs',
  merchandise:'Merchandise',portrait:'Portraits',craft:'Craft',
  activity:'Activity',candles:'Candles',leather:'Leather',
  seasonal:'Seasonal Shop',candy:'Candy',general:'General Store',
  herbal:'Herbal',home_goods:'Home Goods',food_gifts:'Food & Gifts',
  bakery_demo:'Bakery Demo',wax:'Wax Hands',glass:'Glassblowing',
  blacksmith:'Blacksmith',music_store:'Music Store'
}};
const A = {park_js};

// ── Pin badge coordinates (1836×1290 SVG space) ──────────────────────────────
const PIN_COORDS={{1:[1122,928],4:[1116,981],7:[847,988],20:[1075,995],21:[889,997],22:[929,966],23:[1008,1035],24:[898,1027],25:[743,594],26:[797,542],27:[738,668],28:[830,394],29:[676,722],30:[666,629],33:[768,569],34:[770,629],35:[1028,106],36:[1000,195],38:[1093,280],42:[1064,206],43:[984,227],44:[946,244],45:[912,249],46:[914,278],47:[1182,230],48:[1196,286],49:[1194,509],51:[1274,528],52:[1206,102],53:[1320,758],54:[1244,361],68:[1331,721],69:[1264,801],70:[1215,440],71:[1347,820],72:[1352,791],73:[1304,630],74:[1190,78],75:[1156,730],76:[1195,789],77:[1184,698],78:[1703,996],79:[1605,936],80:[1652,995],82:[1554,977],83:[1470,964],84:[1490,984],85:[1760,1151],86:[1626,1073],87:[1694,1192],89:[1750,1105],90:[1734,1175],91:[1730,1143],92:[1632,1103],93:[1665,1068],94:[1753,1052],95:[1656,1156],96:[1629,1201],97:[1715,1105],98:[1539,1088],99:[1559,1139],100:[1601,1035],101:[1699,1132],102:[1651,1132],103:[1344,930],104:[1321,950],105:[1310,1080],111:[1257,949],112:[1198,976],113:[1187,1031],114:[1369,951],115:[1288,1057],116:[1164,982],117:[1182,1009],118:[1211,1167],119:[1254,1137],120:[1140,1125],122:[1181,1143],123:[1133,1098],124:[1203,1089],125:[1029,1084],126:[1082,1082],127:[965,1149],128:[974,1125],129:[1024,1145],131:[269,502],132:[473,413],133:[420,603],134:[421,440],135:[598,525],136:[380,515],137:[72,430],138:[429,555],139:[480,505],140:[720,532],141:[510,486],145:[337,540],146:[149,534],147:[692,491],148:[735,492],149:[448,533]}};

// ── State ────────────────────────────────────────────────────────────────────
let curArea=null, panelPage='list', idetClearTimer=null; // 'list'|'detail'
const isMob=()=>window.innerWidth<768;

// ── View toggle ───────────────────────────────────────────────────────────────
function switchView(v){{
  document.querySelectorAll('.view').forEach(el=>el.classList.remove('on'));
  document.querySelectorAll('.tbtn').forEach(el=>el.classList.remove('on'));
  document.getElementById(v+'-view').classList.add('on');
  event.currentTarget.classList.add('on');
  if(v==='map') closePanel();
  if(v==='list') renderListView();
}}

// ── Map polygon interaction ───────────────────────────────────────────────────
document.querySelectorAll('#msvg polygon').forEach(p=>{{
  p.addEventListener('click',e=>{{e.stopPropagation();if(pz.dragged)return;selectArea(p.dataset.area);}});
  p.addEventListener('touchend',e=>{{if(pz.dragged)return;e.preventDefault();selectArea(p.dataset.area);}});
}});
document.getElementById('mc').addEventListener('click',e=>{{
  if(e.target===document.getElementById('mc')||e.target===document.getElementById('mi')||e.target.tagName==='IMG')closePanel();
}});

function selectArea(key){{
  curArea=key; panelPage='list';
  highlightZone(key);
  pz.zoomTo(key);
  showPanel(key);
}}

// ── Pin badge hit-targets ─────────────────────────────────────────────────────
(function(){{
  const mapIdToItem={{}};
  for(const[key,area]of Object.entries(A)){{
    for(const[cat,items]of[['att',area.att],['din',area.din],['shp',area.shp]]){{
      for(const item of(items||[])){{
        if(item.id>0)mapIdToItem[item.id]={{areaKey:key,cat}};
      }}
    }}
  }}
  const svg=document.getElementById('msvg');
  for(const[idStr,[x,y]]of Object.entries(PIN_COORDS)){{
    const id=+idStr;
    const info=mapIdToItem[id];
    if(!info)continue;
    const{{areaKey,cat}}=info;
    const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx',x);c.setAttribute('cy',y);c.setAttribute('r','30');
    c.setAttribute('fill','transparent');c.style.cursor='pointer';
    const tap=()=>{{
      if(pz.dragged)return;
      if(curArea!==areaKey)selectArea(areaKey);
      openIdet(areaKey,id,cat);
      pz.panToPin(x,y);
    }};
    c.addEventListener('click',e=>{{e.stopPropagation();tap();}});
    c.addEventListener('touchend',e=>{{if(pz.dragged)return;e.preventDefault();e.stopPropagation();tap();}});
    svg.appendChild(c);
  }}
}})();

function highlightZone(key){{
  document.querySelectorAll('#msvg polygon').forEach(p=>{{
    if(p.dataset.area===key){{p.setAttribute('fill-opacity','0.55');p.setAttribute('stroke-width','3');}}
    else{{p.setAttribute('fill-opacity','0.3');p.setAttribute('stroke-width','2');}}
  }});
}}

// ── Panel ────────────────────────────────────────────────────────────────────
function showPanel(key){{
  const area=A[key];
  document.getElementById('p-dot').style.background=area.color;
  document.getElementById('p-title').textContent=area.name;
  document.getElementById('p-back').classList.remove('on');
  renderPanelList(key);
  document.getElementById('panel').classList.add('on');
  closeIdet();
}}

function renderPanelList(key){{
  const area=A[key];
  const wrap=document.createElement('div');
  wrap.className='cs-wrap';
  if(area.att?.length) wrap.appendChild(buildCatSection(area,key,area.att,'att','🎢','Attractions'));
  if(area.din?.length) wrap.appendChild(buildCatSection(area,key,area.din,'din','🍽','Dining'));
  if(area.shp?.length) wrap.appendChild(buildCatSection(area,key,area.shp,'shp','🛍','Shopping'));
  const body=document.getElementById('pbody');
  const idet=document.getElementById('idet');
  body.innerHTML=''; body.appendChild(wrap); body.appendChild(idet);
  wrap.querySelectorAll('.ir').forEach(r=>{{
    r.addEventListener('click',()=>{{
      const id=+r.dataset.id;
      openIdet(key,id,r.dataset.cat);
      const coords=PIN_COORDS[id];
      if(coords) pz.panToPin(coords[0],coords[1]);
    }});
  }});
}}

function buildCatSection(area,areaKey,items,cat,icon,label){{
  const sec=document.createElement('div');sec.className='cs';
  sec.innerHTML=`<div class="cl"><span class="cl-ic ${{cat}}-ic">${{icon}}</span>${{label}}</div>`
    +items.map(i=>{{
      const tags=[
        i.hmin?`<span class="tag h-tag">${{i.hmin}} in</span>`:'',
        i.hmax?`<span class="tag h-tag">${{i.hmax}} in max</span>`:'',
        i.ts===2?'<span class="tag ts-tag ts-prem">TS+</span>':i.ts?'<span class="tag ts-tag">TS</span>':'',
        i.closed?'<span class="tag cl-tag">Closed</span>':'',
        i.seasonal?`<span class="tag sea-tag">${{i.sdates||'Seasonal'}}</span>`:'',
      ].filter(Boolean).join('');
      return `<div class="ir" data-id="${{i.id}}" data-cat="${{cat}}" data-area="${{areaKey}}">
        <span class="in">${{i.id>0?i.id:''}}</span><span class="iname">${{i.name}}</span>
        <span class="itags">${{tags}}</span><span class="iarr">›</span></div>`;
    }}).join('');
  return sec;
}}

function openIdet(key,id,cat){{
  const area=A[key];
  const items=cat==='att'?area.att:cat==='din'?area.din:area.shp;
  const item=items.find(i=>i.id===id); if(!item)return;
  panelPage='detail';
  document.getElementById('p-title').textContent=item.name;
  document.getElementById('p-back').classList.add('on');
  document.getElementById('idet-body').innerHTML=detailHTML(item,area,cat);
  document.getElementById('idet').classList.add('on');
}}

function detailHTML(item,area,cat){{
  const cl=cat==='att'?'att':cat==='din'?'din':'shp';
  const lb=cat==='att'?'Attractions':cat==='din'?'Dining':'Shopping';
  const typeLabel=item.type?(TYPE_LABELS[item.type]||item.type):null;
  const tags=[
    `<span class="det-tag det-${{cl}}">${{lb}}</span>`,
    typeLabel?`<span class="det-tag det-type">${{typeLabel}}</span>`:'',
    item.hmin?`<span class="det-tag det-h">${{item.hmin}} in to ride</span>`:'',
    item.hmax?`<span class="det-tag det-h">max ${{item.hmax}} in to ride</span>`:'',
    item.ts===2?'<span class="det-tag det-tsprem">TimeSaver+ (Premium)</span>':item.ts?'<span class="det-tag det-ts">TimeSaver</span>':'',
    item.closed?'<span class="det-tag det-closed">Temporarily Closed</span>':'',
    item.seasonal?`<span class="det-tag det-sea">Seasonal${{item.sdates?' · '+item.sdates:''}}</span>`:'',
  ].filter(Boolean).join('');
  const venueNote=item.venue?`<div style="font-size:13px;color:var(--txt2);margin-bottom:14px">Venue: ${{item.venue}}</div>`:'';
  const mapPin=item.id>0?`<div class="det-id">Map #${{item.id}}</div>`:'';
  return `<div class="det-area-pill"><div class="det-area-dot" style="background:${{area.color}}"></div>
    <span class="det-area-nm">${{area.name}}</span></div>
    <div class="det-name">${{item.name}}</div>
    ${{mapPin}}
    <div class="det-tags">${{tags}}</div>
    ${{venueNote}}
    ${{item.desc?`<div class="det-info">${{item.desc}}</div>`:''}}`;

}}

function closeIdet(){{
  const el=document.getElementById('idet');
  el.classList.remove('on');
  setTimeout(()=>{{document.getElementById('idet-body').innerHTML='';}},320);
}}
function panelBack(){{
  if(panelPage==='detail'){{
    closeIdet(); panelPage='list';
    document.getElementById('p-back').classList.remove('on');
    if(curArea) document.getElementById('p-title').textContent=A[curArea].name;
  }}
}}
function closePanel(){{
  document.getElementById('panel').classList.remove('on');
  document.querySelectorAll('#msvg polygon').forEach(p=>{{p.setAttribute('fill-opacity','0.3');p.setAttribute('stroke-width','2');}});
  curArea=null;
}}

// ── List view + filters ──────────────────────────────────────────────────────
const RIDE_TYPES=new Set(['roller_coaster','family','water','thrill','pre_k']);
const SHOW_TYPES=new Set(['show','venue','film','interactive_experience','character_meet','dance_party','music','attraction']);
const F={{area:'',cat:'all',hmin:0,ts:false}};

function renderListView(){{
  const body=document.getElementById('list-body');
  const keys=F.area?[F.area]:Object.keys(A);
  const showBadge=!F.area;
  const frag=document.createDocumentFragment();
  let any=false;

  for(const key of keys){{
    const area=A[key];
    let att=(area.att||[]).slice();
    let din=(area.din||[]).slice();
    let shp=(area.shp||[]).slice();

    // Category filter
    if(F.cat==='rides'){{att=att.filter(i=>RIDE_TYPES.has(i.type));din=[];shp=[];}}
    else if(F.cat==='shows'){{att=att.filter(i=>SHOW_TYPES.has(i.type));din=[];shp=[];}}
    else if(F.cat==='din'){{att=[];shp=[];}}
    else if(F.cat==='shp'){{att=[];din=[];}}

    // Height filter (rides only)
    if(F.hmin===-1) att=att.filter(i=>i.hmax>0);
    else if(F.hmin>0) att=att.filter(i=>i.hmin>=F.hmin);

    // TimeSaver filter
    if(F.ts){{
      att=att.filter(i=>i.ts);
      din=din.filter(i=>i.ts);
      shp=shp.filter(i=>i.ts);
    }}

    if(!att.length&&!din.length&&!shp.length) continue;
    any=true;

    const wrap=document.createElement('div'); wrap.className='cs-wrap';

    if(showBadge){{
      const badge=document.createElement('div'); badge.className='area-badge';
      badge.innerHTML=`<div class="area-badge-dot" style="background:${{area.color}}"></div><span>${{area.name}}</span>`;
      wrap.appendChild(badge);
    }}

    if(att.length) wrap.appendChild(buildCatSection(area,key,att,'att','🎢','Attractions'));
    if(din.length) wrap.appendChild(buildCatSection(area,key,din,'din','🍽','Dining'));
    if(shp.length) wrap.appendChild(buildCatSection(area,key,shp,'shp','🛍','Shopping'));

    wrap.querySelectorAll('.ir').forEach(r=>{{
      r.addEventListener('click',()=>openLdet(r.dataset.area,+r.dataset.id,r.dataset.cat));
    }});
    frag.appendChild(wrap);
  }}

  body.innerHTML='';
  if(!any){{
    body.innerHTML='<div class="list-empty">No items match these filters</div>';
  }} else {{
    body.appendChild(frag);
  }}
}}

// Filter controls wiring
document.getElementById('f-area').addEventListener('change',e=>{{F.area=e.target.value;renderListView();}});
document.getElementById('f-height').addEventListener('change',e=>{{F.hmin=+e.target.value;renderListView();}});
document.querySelectorAll('.chip[data-cat]').forEach(btn=>{{
  btn.addEventListener('click',()=>{{
    document.querySelectorAll('.chip[data-cat]').forEach(b=>b.classList.remove('on'));
    btn.classList.add('on');
    F.cat=btn.dataset.cat; renderListView();
  }});
}});
document.getElementById('f-ts').addEventListener('click',function(){{
  F.ts=!F.ts;
  this.classList.toggle('ts-on',F.ts);
  renderListView();
}});

function openLdet(key,id,cat){{
  const area=A[key];
  const items=cat==='att'?area.att:cat==='din'?area.din:area.shp;
  const item=items.find(i=>i.id===id); if(!item)return;
  document.getElementById('ldet-inner').innerHTML=`<div style="padding:20px 16px 0">${{detailHTML(item,area,cat)}}</div>`;
  document.getElementById('ldet').classList.add('on');
}}
function closeLdet(){{document.getElementById('ldet').classList.remove('on');}}

// ── Pan / zoom ────────────────────────────────────────────────────────────────
const pz=(()=>{{
  const mc=document.getElementById('mc'), mi=document.getElementById('mi');
  let s=1,tx=0,ty=0,dragged=false;
  let t0=[],pd=0,pm=null;
  let mdown=false,lm=null;

  function apply(ani){{
    mi.style.transition=ani?'transform .42s cubic-bezier(.32,.72,0,1)':'none';
    mi.style.transform=`translate(${{tx}}px,${{ty}}px) scale(${{s}})`;
  }}
  function clamp(){{apply(false);}}
  function dst(t){{const dx=t[0].clientX-t[1].clientX,dy=t[0].clientY-t[1].clientY;return Math.sqrt(dx*dx+dy*dy);}}
  function mid(t){{return{{x:(t[0].clientX+t[1].clientX)/2,y:(t[0].clientY+t[1].clientY)/2}};}}

  mc.addEventListener('touchstart',e=>{{
    e.preventDefault(); dragged=false;
    t0=Array.from(e.touches);
    if(t0.length===2){{pd=dst(t0);pm=mid(t0);}}
  }},{{passive:false}});
  mc.addEventListener('touchmove',e=>{{
    e.preventDefault(); const t=Array.from(e.touches); dragged=true;
    if(t.length===2){{
      const d=dst(t),m=mid(t),r=d/pd;
      const rect=mc.getBoundingClientRect();
      const cx=m.x-rect.left,cy=m.y-rect.top;
      const ns=Math.min(5,Math.max(1,s*r)),sr=ns/s;
      tx=cx-sr*(cx-tx); ty=cy-sr*(cy-ty); s=ns;
      if(pm){{tx+=m.x-pm.x;ty+=m.y-pm.y;}}
      pd=d; pm=m;
    }} else if(t.length===1&&t0.length===1){{
      tx+=t[0].clientX-t0[0].clientX; ty+=t[0].clientY-t0[0].clientY; t0=t;
    }}
    apply(false);
  }},{{passive:false}});
  mc.addEventListener('touchend',e=>{{
    t0=Array.from(e.touches); if(!t0.length)clamp();
  }});
  mc.addEventListener('mousedown',e=>{{mdown=true;lm={{x:e.clientX,y:e.clientY}};dragged=false;mc.classList.add('grab');}});
  window.addEventListener('mousemove',e=>{{
    if(!mdown)return; const dx=e.clientX-lm.x,dy=e.clientY-lm.y;
    if(Math.abs(dx)+Math.abs(dy)>4)dragged=true;
    tx+=dx;ty+=dy;lm={{x:e.clientX,y:e.clientY}};apply(false);
  }});
  window.addEventListener('mouseup',()=>{{if(mdown){{mdown=false;mc.classList.remove('grab');clamp();}}}});
  mc.addEventListener('wheel',e=>{{
    e.preventDefault();
    const r=mc.getBoundingClientRect();
    const cx=e.clientX-r.left,cy=e.clientY-r.top;
    const d=e.deltaY>0?.88:1.14;
    const ns=Math.min(5,Math.max(1,s*d)),sr=ns/s;
    tx=cx-sr*(cx-tx);ty=cy-sr*(cy-ty);s=ns;apply(false);
  }},{{passive:false}});

  function zoomTo(key){{
    const area=A[key];
    const cw=mc.clientWidth,ch=mc.clientHeight;
    const panH=isMob()?ch*.52:ch*.38;
    const visH=ch-panH;
    const iw=mi.offsetWidth,ih=mi.offsetHeight;
    const px=(area.cx/1836)*iw,py=(area.cy/1290)*ih;
    const ts=isMob()?2.2:1.8;
    s=Math.min(5,Math.max(1,ts));
    tx=cw/2-px*s; ty=visH*.4-py*s;
    apply(true); setTimeout(clamp,440);
  }}
  function panToPin(px1836,py1836){{
    const cw=mc.clientWidth,ch=mc.clientHeight;
    const panH=isMob()?ch*.52:ch*.38;
    const visH=ch-panH;
    const iw=mi.offsetWidth,ih=mi.offsetHeight;
    const px=(px1836/1836)*iw,py2=(py1836/1290)*ih;
    tx=cw/2-px*s; ty=visH*.4-py2*s;
    apply(true); setTimeout(clamp,440);
  }}
  return {{zoomTo,panToPin,get dragged(){{return dragged;}}}};
}})();
</script>
</body>
</html>
'''

out = os.path.join(PROJECT, 'index.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Written: {out}  ({os.path.getsize(out):,} bytes)')
