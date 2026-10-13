"""Local-only page editor. No dependencies beyond Python's standard library."""
import argparse, hashlib, json, mimetypes, os, secrets, threading, time, webbrowser, logging
from datetime import datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
PORT = 8767
LOCK = threading.Lock()
TOKEN = secrets.token_urlsafe(32)

def digest(data): return hashlib.sha256(data).hexdigest()
def safe_asset(url):
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or parts.query or parts.fragment: return False
    path = (ROOT / unquote(parts.path)).resolve()
    return path.is_relative_to(ROOT / 'assets') and path.is_file()

class PageCheck(HTMLParser):
    def __init__(self): super().__init__(); self.ids = []; self.main = False; self.scripts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('iframe', 'object', 'embed', 'base', 'form', 'style'): raise ValueError('Unzulässiges HTML-Element.')
        if any(k.lower().startswith('on') or k in ('contenteditable', 'draggable', 'srcdoc') for k in a): raise ValueError('Bearbeitungshilfen dürfen nicht gespeichert werden.')
        if a.get('id'): self.ids.append(a['id'])
        if tag == 'main': self.main = True
        if tag == 'script':
            if a.get('src') not in ('navigation.js', 'progress.js'): raise ValueError('Unzulässiges Skript.')
            self.scripts.append(a['src'])
        if tag == 'img' and not safe_asset(a.get('src', '')): raise ValueError('Bilddatei fehlt oder liegt außerhalb des Bildordners.')
        if tag == 'link' and a.get('rel') == 'stylesheet' and a.get('href') != 'styles.css': raise ValueError('Unzulässiges Stylesheet.')
        for key in ('href', 'src'):
            if a.get(key, '').strip().lower().startswith(('javascript:', 'data:', 'file:')): raise ValueError('Unzulässiger Link.')
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs)

def check_page(html):
    c = PageCheck(); c.feed(html)
    if not c.main or not {'lernangebot', 'studienprojekt', 'inhalt'}.issubset(c.ids): raise ValueError('Die Seitenbereiche fehlen.')
    if len(c.ids) != len(set(c.ids)) or c.scripts not in (['navigation.js'], ['navigation.js', 'progress.js']): raise ValueError('Die Seitenstruktur ist ungültig.')
    if 'data-editor' in html: raise ValueError('Bearbeitungshilfen sind noch enthalten.')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def log_error(self, fmt, *args): logging.error(fmt, *args)
    def host_ok(self): return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')
    def reply(self, code, data, mime='application/json; charset=utf-8'):
        if not isinstance(data, bytes): data = json.dumps(data, ensure_ascii=False).encode('utf8')
        self.send_response(code); self.send_header('Content-Type', mime); self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if not self.host_ok(): return self.reply(403, {'error':'Zugriff nur lokal.'})
        route = urlsplit(self.path).path
        if route == '/api/ping': return self.reply(200, {'app':'deeskalation-editor', 'root':digest(str(ROOT).encode())})
        if route in ('/', '/editor'):
            data = (ROOT/'index.html').read_bytes(); html = data.decode('utf8')
            extra = f'<meta name="editor-token" content="{TOKEN}"><meta name="editor-version" content="{digest(data)}"><link rel="stylesheet" href="editor.css"><script src="editor.js" defer></script>'
            return self.reply(200, html.replace('</head>', extra+'</head>').encode('utf8'), 'text/html; charset=utf-8')
        name = unquote(route.lstrip('/')); path = (ROOT/name).resolve()
        allowed = name in ('index.html','styles.css','navigation.js','progress.js','editor.js','editor.css') or (path.is_relative_to(ROOT/'assets') and path.is_file())
        if not path.is_relative_to(ROOT) or not allowed or not path.is_file(): return self.reply(404, {'error':'Datei nicht gefunden.'})
        return self.reply(200, path.read_bytes(), mimetypes.guess_type(name)[0] or 'application/octet-stream')
    def do_POST(self):
        if not self.host_ok() or self.headers.get('X-Editor-Token') != TOKEN: return self.reply(403, {'error':'Ungültiger Editor-Zugang. Seite neu öffnen.'})
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'): return self.reply(403, {'error':'Ungültiger Ursprung.'})
        route = urlsplit(self.path).path
        if route not in ('/api/save','/api/image','/api/stop'): return self.reply(404, {'error':'Unbekannte Aktion.'})
        if route == '/api/stop':
            self.reply(200, {'stopped':True})
            threading.Thread(target=self.server.shutdown,daemon=True).start()
            return
        try:
            length = int(self.headers.get('Content-Length','0'))
            if length <= 0 or length > 10*1024*1024: return self.reply(413, {'error':'Maximal 10 MB pro Datei.'})
            raw = self.rfile.read(length)
            if route == '/api/image':
                ext = None
                if raw.startswith(b'\x89PNG\r\n\x1a\n'): ext = '.png'
                elif raw.startswith(b'\xff\xd8\xff'): ext = '.jpg'
                elif raw.startswith((b'GIF87a',b'GIF89a')): ext = '.gif'
                elif raw.startswith(b'RIFF') and raw[8:12] == b'WEBP': ext = '.webp'
                if not ext: raise ValueError('Bitte PNG, JPG, GIF oder WebP verwenden.')
                folder=ROOT/'assets/uploads'; folder.mkdir(parents=True,exist_ok=True)
                target=folder/(digest(raw)+ext)
                if not target.exists(): target.write_bytes(raw)
                return self.reply(200, {'src':target.relative_to(ROOT).as_posix()})
            payload=json.loads(raw); html=payload['html']; check_page(html)
            data=html.encode('utf8')
            with LOCK:
                target=ROOT/'index.html'; previous=target.read_bytes()
                if payload.get('version') != digest(previous): return self.reply(409, {'error':'Die Datei wurde zwischenzeitlich geändert. Speichern abgebrochen; bitte deine offenen Änderungen sichern und die Seite neu laden.'})
                folder=ROOT/'sicherungen'; folder.mkdir(exist_ok=True)
                backup=folder/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-index.html')
                backup.write_bytes(previous)
                tmp=ROOT/'.index-editor.tmp'; tmp.write_bytes(data); os.replace(tmp,target)
            return self.reply(200, {'version':digest(data), 'backup':backup.relative_to(ROOT).as_posix()})
        except (ValueError,KeyError,TypeError,UnicodeError) as e: return self.reply(400, {'error':str(e)})
        except OSError: return self.reply(500, {'error':'Speichern fehlgeschlagen. Bitte prüfen, ob die Festplatte verbunden und beschreibbar ist.'})

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--open',action='store_true'); parser.add_argument('--port',type=int,default=PORT); args=parser.parse_args()
    url=f'http://127.0.0.1:{args.port}/editor'
    try: server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError:
        try:
            with urlopen(f'http://127.0.0.1:{args.port}/api/ping',timeout=2) as response: info=json.load(response)
            if info.get('app') != 'deeskalation-editor' or info.get('root') != digest(str(ROOT).encode()): raise RuntimeError('Port bereits anderweitig belegt.')
            if args.open: webbrowser.open(url)
            return
        except Exception: raise RuntimeError(f'Port {args.port} ist belegt. Bitte den vorhandenen Prozess prüfen.')
    if args.open: webbrowser.open(url)
    server.serve_forever()

if __name__ == '__main__':
    logdir=ROOT/'.local';logdir.mkdir(exist_ok=True)
    logging.basicConfig(filename=str(logdir/'editor.log'),level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf8')
    try:
        logging.info('Lokaler Editor gestartet.')
        main()
        logging.info('Lokaler Editor beendet.')
    except Exception:
        logging.exception('Start des lokalen Editors fehlgeschlagen.')
