# app.py
import os, base64, random
from pathlib import Path
from datetime import datetime, timezone, timedelta

import streamlit as st
from streamlit.components.v1 import html as components_html

# yfinance opcional
try:
    import yfinance as yf
    YFINANCE_OK = True
except Exception:
    YFINANCE_OK = False

# =========================
# Config
# =========================
st.set_page_config(page_title="AGBROTHERS Ticker", layout="wide", page_icon="📊")

# =========================
# Sidebar
# =========================
st.sidebar.header("⚙️ Opciones")

data_src = st.sidebar.radio("Fuente de datos", ["FAKE (demo)", "LIVE (yfinance)"], index=0)
speed_s  = st.sidebar.slider("Velocidad scroll (seg/loop)", 20, 120, 50)
gap_px   = st.sidebar.slider("Espacio entre activos (px)", 10, 40, 23)
height_px= st.sidebar.slider("Altura barra (px)", 36, 72, 52)

# Panel/logo que desfila DENTRO de la cinta
logo_path_input = st.sidebar.text_input("Logo (ruta local o URL)", "LOGO1.png")
panel_w   = st.sidebar.slider("Ancho del panel de logo en la cinta (px)", 220, 800, 600)
panel_h   = st.sidebar.slider("Alto del logo dentro del panel (px)", 28, 120, 64)
every_n   = st.sidebar.slider("Insertar el logo cada N activos", 3, 12, 6)

# (opcional) Logo fijo a la derecha + reserva
use_fixed_logo = st.sidebar.checkbox("Logo fijo a la derecha (además del logo en la cinta)", False)
fixed_logo_h   = st.sidebar.slider("Alto logo fijo (px)", 20, 120, 44, disabled=not use_fixed_logo)
right_reserve  = st.sidebar.slider("Reserva derecha (px) si logo fijo", 160, 360, 260, disabled=not use_fixed_logo)

dark     = st.sidebar.checkbox("Tema oscuro (preview)", True)
overlay  = st.sidebar.checkbox("Overlay OBS (fondo transparente)", True)
clock_px = st.sidebar.slider("Tamaño del reloj (px)", 14, 28, 20)
# Este autorefresco solo recarga Streamlit (para precios). El reloj ya es JS y no lo necesita.
auto_refresh = st.sidebar.slider("Autorefrescar app cada (seg) para datos", 0, 60, 0)

# =========================
# Datos
# =========================
INDICES = ["SPX","NDX","DJI","RUT","VIX"]
STOCKS  = ["AAPL","MSFT","AMZN","NVDA","TSLA","META","GOOG","AMD","NFLX","JPM","BRK.B"]
CRYPTO  = ["BTCUSD","ETHUSD","SOLUSD","BNBUSD","XRPUSD"]
SEQUENCE = INDICES + STOCKS + CRYPTO

def fmt_price(x): 
    return f"{x:,.2f}".replace(",", " ")

def snapshot_fake(symbols):
    rnd = random.Random()
    return [(s, round(rnd.uniform(50, 5000), 2), rnd.uniform(-2, 2)) for s in symbols]

YF_MAP = {
    "SPX":"^GSPC","NDX":"^NDX","DJI":"^DJI","RUT":"^RUT","VIX":"^VIX",
    "AAPL":"AAPL","MSFT":"MSFT","AMZN":"AMZN","NVDA":"NVDA","TSLA":"TSLA",
    "META":"META","GOOG":"GOOG","AMD":"AMD","NFLX":"NFLX","JPM":"JPM","BRK.B":"BRK-B",
    "BTCUSD":"BTC-USD","ETHUSD":"ETH-USD","SOLUSD":"SOL-USD","BNBUSD":"BNB-USD","XRPUSD":"XRP-USD"
}

def snapshot_live(symbols):
    if not YFINANCE_OK:
        return None
    try:
        tickers = [YF_MAP[s] for s in symbols]
        data = yf.download(" ".join(tickers), period="1d", interval="1m",
                           group_by="ticker", progress=False, threads=True)
        rows = []
        for s in symbols:
            t = YF_MAP[s]
            df = data[t]
            last = float(df["Close"].dropna().iloc[-1])
            prev = (yf.Ticker(t).info or {}).get("previousClose") or last
            chg  = ((last/prev) - 1.0) * 100.0
            rows.append((s, last, chg))
        return rows
    except Exception:
        return None

rows = snapshot_live(SEQUENCE) if data_src.startswith("LIVE") else snapshot_fake(SEQUENCE)
if rows is None:
    rows = snapshot_fake(SEQUENCE)

def items_html(rows):
    parts = []
    for s, price, chg in rows:
        arrow = "▲" if chg >= 0 else "▼"
        cls   = "up" if chg >= 0 else "down"
        parts.append(
            f"""
            <span class="ticker-item">
              <span class="ticker-symbol">{s}</span>
              <span class="ticker-price">{fmt_price(price)}</span>
              <span class="ticker-chg {cls}">{arrow} {abs(chg):.2f}%</span>
            </span>
            <span class="ticker-sep">|</span>
            """
        )
    return parts

# =========================
# Logo (local o URL) -> base64
# =========================
def is_url(s: str) -> bool:
    return s.lower().startswith(("http://", "https://"))

def load_logo_b64(path_or_url: str):
    try:
        if is_url(path_or_url):
            import requests
            r = requests.get(path_or_url, timeout=10)
            r.raise_for_status()
            return base64.b64encode(r.content).decode()
        else:
            path = Path(__file__).parent / path_or_url  # relativo a app.py
            if path.exists():
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return None

logo64 = load_logo_b64(logo_path_input)

panel_html = f"""
  <span class="panel-logo" style="width:{panel_w}px">
    {"<img src='data:image/png;base64,"+logo64+"'/>" if logo64 else "<strong>AGBROTHERS</strong>"}
  </span>
"""

# Intercalar el logo cada N activos
def build_track_with_logos(rows, every=6):
    pieces = []
    items = items_html(rows)
    for i, html_item in enumerate(items, start=1):
        pieces.append(html_item)
        if i % every == 0:
            pieces.append(panel_html)
    return "".join(pieces)

# =========================
# Estilos y HTML (iframe)
# =========================
bg_color = "rgba(0,0,0,0)" if overlay else ("#000" if dark else "#fff")
page_bg  = "#111518" if dark else "#ffffff"
brand    = "#0a1626"
text     = "#ffffff" if dark else "#000000"

track_once = build_track_with_logos(rows, every=every_n)
track_content = track_once + track_once  # scroll infinito

fixed_logo_img = ""
if use_fixed_logo and logo64:
    fixed_logo_img = f"<img id='ag-fixed-logo' src='data:image/png;base64,{logo64}'/>"

html_code = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  html,body {{
    margin:0; padding:0; overflow:hidden;
    background:{page_bg};
  }}
  :root {{
    --h:{height_px}px;
    --gap:{gap_px}px;
    --speed:{speed_s}s;
  }}
  .ticker-fixed-bottom {{
    position: fixed;
    left: 0; right: 0; bottom: 0;
    height: var(--h);
    background: {bg_color};
    color: {text};
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Arial, sans-serif;
    border-top: 1px solid rgba(255,255,255,.12);
    z-index: 2147483000;
  }}
  .ticker-inner {{
    position: relative; height: 100%; width: 100%; overflow: hidden; z-index: 2;
  }}
  .ticker-track {{
    position: absolute; top: 0; left: 0; height: 100%;
    display: inline-flex; align-items: center; gap: var(--gap);
    white-space: nowrap;
    padding-left: var(--gap);
    padding-right: {"%d" % (right_reserve if use_fixed_logo else 12)}px;
    width: max-content;
    transform: translateZ(0);
    animation: scroll-left var(--speed) linear infinite;
  }}
  @keyframes scroll-left {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
  }}

  .ticker-item {{ display:inline-flex; align-items:center; gap:8px; font-size:14px; font-weight:600; line-height:1; }}
  .ticker-symbol {{ font-weight:800; letter-spacing:.3px; }}
  .ticker-chg.up   {{ color:#00d26a; font-weight:800; }}
  .ticker-chg.down {{ color:#ff3b3b; font-weight:800; }}
  .ticker-sep {{ color:#9aa0a6; opacity:.9; margin:0 2px; }}

  .panel-logo {{
    display:inline-flex; align-items:center; justify-content:center;
    height: calc(var(--h) - 10px);
    border-radius:10px; padding: 0 10px;
    background: linear-gradient(90deg, rgba(10,22,38,.65), rgba(10,22,38,.35));
    border:1px solid #15283f;
    box-shadow: 0 0 12px rgba(0,210,255,.25) inset;
    margin: 0 6px;
  }}
  .panel-logo img {{ height:{panel_h}px; width:auto; display:block; }}

  .ticker-right {{
    position:absolute; right:8px; top:0; height:100%;
    display:{'flex' if use_fixed_logo else 'none'};
    align-items:center; gap:10px; z-index: 3;
  }}
  #ag-fixed-logo {{ height:{fixed_logo_h}px; width:auto; border-radius:6px; }}
  #clockNY {{
    padding:0 14px; height: calc(var(--h) - 10px);
    display:flex; align-items:center; justify-content:center;
    background:{brand}; color:#fff; font-weight:900; border-radius:8px;
    border:1px solid #15283f; font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size:{clock_px}px;
  }}
</style>
</head>
<body>
  <div class="ticker-fixed-bottom">
    <div class="ticker-inner">
      <div class="ticker-track">
        {track_content}
      </div>
    </div>
    <div class="ticker-right">
      {fixed_logo_img}
      <div id="clockNY"></div>
    </div>
  </div>

  <!-- Reloj dinámico en cliente -->
  <script>
    function updateNYClock() {{
      try {{
        const fmt = new Intl.DateTimeFormat('en-US', {{
          timeZone: 'America/New_York',
          hour12: false,
          hour: '2-digit',
          minute: '2-digit'
        }});
        const parts = fmt.formatToParts(new Date());
        const hh = parts.find(p => p.type === 'hour').value;
        const mm = parts.find(p => p.type === 'minute').value;
        const el = document.getElementById('clockNY');
        if (el) el.textContent = `${{hh}}:${{mm}} NY`;
      }} catch(e) {{
        // fallback simple
        const d = new Date();
        const hh = String(d.getUTCHours() - 5).padStart(2,'0');
        const mm = String(d.getMinutes()).padStart(2,'0');
        const el = document.getElementById('clockNY');
        if (el) el.textContent = `${{hh}}:${{mm}} NY`;
      }}
    }}
    updateNYClock();
    setInterval(updateNYClock, 5000); // cada 5s
  </script>
</body>
</html>
"""

# Render en iframe (abajo)
components_html(html_code, height=height_px + 6)

# Autorefresco opcional para actualizar datos (no necesario para el reloj)
if auto_refresh and auto_refresh > 0:
    import time
    time.sleep(auto_refresh)
    st.experimental_rerun()
