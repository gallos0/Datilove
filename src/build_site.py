#!/usr/bin/env python3
"""Gera o site público do Datilove (GitHub Pages) a partir de /home/claude/datilove/index.html.

Uso: python3 build_site.py [URL_BASE]
Saída: /home/claude/site/out
"""
import base64, re, sys, os, time, zipfile, shutil

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://gallos0.github.io/Datilove/").rstrip("/") + "/"
APP_URL = BASE + "app/"
SRC = "/home/claude/datilove/index.html"
FONTS = "/home/claude/build/node_modules/@fontsource/"
OUT = "/home/claude/site/out"
VERSION = time.strftime("%Y%m%d%H%M%S")

os.makedirs(OUT + "/app", exist_ok=True)
os.makedirs(OUT + "/downloads", exist_ok=True)

# ---------- app page: fonts embedded + PWA hooks ----------
faces = [
    ("Special Elite", "special-elite/files/special-elite-latin-400-normal.woff2", "normal", 400),
    ("Courier Prime", "courier-prime/files/courier-prime-latin-400-normal.woff2", "normal", 400),
    ("Courier Prime", "courier-prime/files/courier-prime-latin-400-italic.woff2", "italic", 400),
    ("Courier Prime", "courier-prime/files/courier-prime-latin-700-normal.woff2", "normal", 700),
    ("Courier Prime", "courier-prime/files/courier-prime-latin-700-italic.woff2", "italic", 700),
    ("Cutive Mono", "cutive-mono/files/cutive-mono-latin-400-normal.woff2", "normal", 400),
]
css = "".join(
    f"@font-face{{font-family:'{n}';font-style:{s};font-weight:{w};font-display:block;"
    f"src:url(data:font/woff2;base64,{base64.b64encode(open(FONTS + p, 'rb').read()).decode()}) format('woff2')}}\n"
    for n, p, s, w in faces
)
h = open(SRC, encoding="utf-8").read()
h = re.sub(r'<link rel="preconnect"[^>]*>\n', "", h)
h = re.sub(r'<link href="https://fonts.googleapis.com[^>]*>\n', "<style>\n" + css + "</style>\n", h)
assert "googleapis" not in h
head = (
    '<link rel="manifest" href="../manifest.webmanifest">\n'
    '<meta name="theme-color" content="#050505">\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-title" content="Datilove">\n'
    '<link rel="icon" href="../icons/favicon-32.png">\n'
    '<link rel="apple-touch-icon" href="../icons/apple-touch-icon.png">\n'
)
h = h.replace("<title>Datilove</title>\n", "<title>Datilove</title>\n" + head, 1)
sw = (
    "<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('../sw.js')"
    ".then(r=>{r.update();setInterval(()=>r.update(),3600000)}).catch(()=>{});"
    "let reloaded=false;navigator.serviceWorker.addEventListener('controllerchange',()=>{"
    "if(reloaded||document.querySelector('#lines .g'))return;reloaded=true;location.reload()})}</script>\n"
)
h = h.replace("</body>", sw + "</body>", 1)
open(OUT + "/app/index.html", "w", encoding="utf-8").write(h)

# ---------- manifest + service worker ----------
open(OUT + "/manifest.webmanifest", "w", encoding="utf-8").write("""{
  "name": "Datilove",
  "short_name": "Datilove",
  "description": "Uma máquina de escrever para o seu computador.",
  "lang": "pt-BR",
  "id": "./app/",
  "start_url": "./app/",
  "scope": "./",
  "display": "standalone",
  "background_color": "#050505",
  "theme_color": "#050505",
  "icons": [
    {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
    {"src": "icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
""")
open(OUT + "/sw.js", "w", encoding="utf-8").write(f"""// Datilove — versão {VERSION}
// Rede primeiro: com internet, sempre carrega a versão mais nova; sem internet, usa a última guardada.
const CACHE = 'datilove-{VERSION}';
const CORE = ['./', './app/', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png'];
self.addEventListener('install', e => {{ self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).catch(() => {{}})); }});
self.addEventListener('activate', e => {{ e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); }});
self.addEventListener('fetch', e => {{
  const r = e.request;
  if (r.method !== 'GET' || new URL(r.url).origin !== location.origin) return;
  e.respondWith(fetch(r, {{cache: 'no-cache'}}).then(res => {{
    if (res.ok) {{ const copy = res.clone(); caches.open(CACHE).then(c => c.put(r, copy)); }}
    return res;
  }}).catch(() => caches.match(r, {{ignoreSearch: true}}).then(m => m || caches.match('./app/'))));
}});
""")

# ---------- launchers ----------
def zwrite(z, name, data, mode=0o644):
    zi = zipfile.ZipInfo(name, date_time=time.localtime()[:6])
    zi.external_attr = (0o100000 | mode) << 16
    zi.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(zi, data)

def zdir(z, name):
    zi = zipfile.ZipInfo(name, date_time=time.localtime()[:6])
    zi.external_attr = (0o040755 << 16) | 0x10
    z.writestr(zi, b"")

mac_script = f"""#!/bin/bash
# Datilove — abre a versão sempre atualizada numa janela própria
URL="{APP_URL}"
PROFILE="$HOME/Library/Application Support/Datilove"
mkdir -p "$PROFILE"
if open -Ra "Google Chrome" 2>/dev/null; then
  open -na "Google Chrome" --args --app="$URL" --user-data-dir="$PROFILE" --window-size=1320,880 --no-first-run --no-default-browser-check
elif open -Ra "Microsoft Edge" 2>/dev/null; then
  open -na "Microsoft Edge" --args --app="$URL" --user-data-dir="$PROFILE" --window-size=1320,880 --no-first-run
else
  open "$URL"
fi
"""
plist = open("/mnt/user-data/outputs/Datilove.app/Contents/Info.plist", encoding="utf-8").read()
with zipfile.ZipFile(OUT + "/downloads/Datilove-Mac.zip", "w") as z:
    for d in ("Datilove.app/", "Datilove.app/Contents/", "Datilove.app/Contents/MacOS/", "Datilove.app/Contents/Resources/"):
        zdir(z, d)
    zwrite(z, "Datilove.app/Contents/Info.plist", plist)
    zwrite(z, "Datilove.app/Contents/PkgInfo", "APPL????")
    zwrite(z, "Datilove.app/Contents/MacOS/Datilove", mac_script, 0o755)
    zwrite(z, "Datilove.app/Contents/Resources/AppIcon.icns", open("/home/claude/build/AppIcon.icns", "rb").read())

win_cmd = f"""@echo off
rem Datilove - abre a versao sempre atualizada numa janela propria
start "" msedge --app={APP_URL} --window-size=1320,880
if errorlevel 1 start "" {APP_URL}
""".replace("\n", "\r\n")
win_readme = f"""Datilove para Windows\r
\r
1. Clique duas vezes em Datilove.cmd para abrir.\r
2. Para fixar: com o Datilove aberto, clique com o botao direito no icone da barra de tarefas e escolha Fixar na barra de tarefas.\r
\r
Dica: o jeito mais completo e abrir {APP_URL} no Microsoft Edge ou no Chrome e clicar em Instalar (icone na barra de endereco).\r
O Datilove se atualiza sozinho sempre que abrir com internet.\r
"""
with zipfile.ZipFile(OUT + "/downloads/Datilove-Windows.zip", "w") as z:
    zwrite(z, "Datilove/Datilove.cmd", win_cmd)
    zwrite(z, "Datilove/LEIA-ME.txt", win_readme)

# ---------- landing page ----------
landing = open("/home/claude/site/landing.html", encoding="utf-8").read().replace("{{APP_URL}}", APP_URL)
open(OUT + "/index.html", "w", encoding="utf-8").write(landing)
open(OUT + "/.nojekyll", "w").write("")
print("site ok", VERSION, APP_URL)
