"""Local-only page editor. No dependencies beyond Python's standard library."""
import argparse, hashlib, json, mimetypes, os, re, secrets, threading, time, webbrowser, logging
from datetime import datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
PORT = 8767
LOCK = threading.Lock()
TOKEN = secrets.token_urlsafe(32)
EDITABLE_PAGES = {'index.html': 'Startseite', 'lerneinheiten/glasl.html': 'Glasl',
                  'lerneinheiten/watzlawick.html': 'Watzlawick', 'lerneinheiten/schulz-von-thun.html': 'Schulz von Thun'}

def digest(data): return hashlib.sha256(data).hexdigest()
def local_path(url, page='index.html'):
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or parts.query or parts.fragment: return None
    value = unquote(parts.path)
    base = ROOT if value.startswith('/') else (ROOT/page).parent
    return (base/value.lstrip('/')).resolve()

def safe_asset(url, page='index.html'):
    path = local_path(url, page)
    return bool(path and path.is_relative_to(ROOT/'assets') and path.is_file())

class PageCheck(HTMLParser):
    def __init__(self, page):
        super().__init__(); self.page=page; self.ids=[]; self.main=False; self.scripts=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in ('iframe','object','embed','base','form','style'): raise ValueError('Unzulässiges HTML-Element.')
        if any(k.lower().startswith('on') or k in ('contenteditable','draggable','srcdoc') for k in a): raise ValueError('Bearbeitungshilfen dürfen nicht gespeichert werden.')
        if a.get('id'): self.ids.append(a['id'])
        if tag=='main': self.main=True
        if tag=='script':
            if self.page!='index.html' or a.get('src') not in ('navigation.js','progress.js'): raise ValueError('Unzulässiges Skript.')
            self.scripts.append(a['src'])
        if tag=='img' and not safe_asset(a.get('src',''),self.page): raise ValueError('Bilddatei fehlt oder liegt außerhalb des Bildordners.')
        if tag in ('source','track') and not safe_asset(a.get('src',''),self.page): raise ValueError('Mediendatei fehlt oder liegt außerhalb des Medienordners.')
        if tag=='video':
            for key in ('src','poster'):
                if a.get(key) and not safe_asset(a[key],self.page): raise ValueError('Unzulässige Mediendatei.')
        if tag=='link' and a.get('rel')=='stylesheet' and local_path(a.get('href',''),self.page)!=ROOT/'styles.css': raise ValueError('Unzulässiges Stylesheet.')
        for key in ('href','src'):
            if a.get(key,'').strip().lower().startswith(('javascript:','data:','file:')): raise ValueError('Unzulässiger Link.')
    def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs)

def check_page(html, page='index.html'):
    if page not in EDITABLE_PAGES: raise ValueError('Diese Seite kann nicht bearbeitet werden.')
    c=PageCheck(page); c.feed(html)
    required={'lernangebot','studienprojekt','inhalt'} if page=='index.html' else {'inhalt'}
    scripts_ok=c.scripts in (['navigation.js'],['navigation.js','progress.js']) if page=='index.html' else not c.scripts
    if not c.main or not required.issubset(c.ids): raise ValueError('Die Seitenbereiche fehlen.')
    if len(c.ids)!=len(set(c.ids)) or not scripts_ok: raise ValueError('Die Seitenstruktur ist ungültig.')
    if 'data-editor' in html: raise ValueError('Bearbeitungshilfen sind noch enthalten.')

class LessonText(HTMLParser):
    def __init__(self): super().__init__(); self.level=0; self.active=False; self.skip_link=False; self.parts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='section':
            if a.get('id') in ('lerntext','quellen'): self.active=True
            if self.active:self.level+=1
        if not self.active:return
        if tag=='a' and 'download' in a:self.skip_link=True
        if tag in ('h2','h3','p','summary','li'):self.parts.append('\n\n')
        if tag=='a' and not self.skip_link and a.get('href','').startswith('https://'):self.parts.append(a['href']+' ')
        if tag=='br':self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag=='a':self.skip_link=False
        if tag=='section' and self.active:
            self.level-=1
            if not self.level:self.active=False
    def handle_data(self,data):
        if self.active and not self.skip_link:self.parts.append(data)
    def text(self):
        return 'Eskalationsmodell nach Friedrich Glasl\n\n'+re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',''.join(self.parts)).strip()+'\n'

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
    def send_media(self, path, mime):
        # Single byte ranges let browser video controls seek before full download.
        size = path.stat().st_size
        start, end, status = 0, size - 1, 200
        header = self.headers.get('Range')
        if header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
            valid = bool(match and any(match.groups()) and size)
            if valid:
                a, b = match.groups()
                if a:
                    start = int(a)
                    end = min(int(b), size - 1) if b else size - 1
                    valid = start < size and start <= end
                else:
                    suffix = int(b)
                    valid = suffix > 0
                    start = max(0, size - suffix)
            if not valid:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                return
            status = 206
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        try:
            with path.open('rb') as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining:
                    block = stream.read(min(256 * 1024, remaining))
                    if not block: break
                    self.wfile.write(block)
                    remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Browsers cancel one range when seeking to another.

    def editor_extra(self, data, page):
        prefix='../' if page.startswith('lerneinheiten/') else ''
        return f'<meta name="editor-token" content="{TOKEN}"><meta name="editor-version" content="{digest(data)}"><meta name="editor-page" content="{page}"><link rel="stylesheet" href="{prefix}editor.css" data-editor="stylesheet"><script src="{prefix}editor.js" data-editor="script" defer></script>'
    def do_GET(self):
        if not self.host_ok(): return self.reply(403, {'error':'Zugriff nur lokal.'})
        route = urlsplit(self.path).path
        if route == '/api/ping': return self.reply(200, {'app':'deeskalation-editor', 'root':digest(str(ROOT).encode())})
        if route in ('/', '/editor'):
            data = (ROOT/'index.html').read_bytes(); html = data.decode('utf8')
            extra = self.editor_extra(data, 'index.html')
            return self.reply(200, html.replace('</head>', extra+'</head>').encode('utf8'), 'text/html; charset=utf-8')
        name = unquote(route.lstrip('/')); path = (ROOT/name).resolve()
        allowed = name in ('index.html','styles.css','navigation.js','progress.js','editor.js','editor.css','lerneinheiten/glasl.html','lerneinheiten/watzlawick.html','lerneinheiten/schulz-von-thun.html') or (path.is_relative_to(ROOT/'assets') and path.is_file())
        if not path.is_relative_to(ROOT) or not allowed or not path.is_file(): return self.reply(404, {'error':'Datei nicht gefunden.'})
        if name in EDITABLE_PAGES and parse_qs(urlsplit(self.path).query).get('editor')==['1']:
            data=path.read_bytes()
            html=data.decode('utf8').replace('</head>', self.editor_extra(data,name)+'</head>')
            return self.reply(200,html.encode('utf8'),'text/html; charset=utf-8')
        mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        if mime.startswith(('video/', 'audio/')): return self.send_media(path, mime)
        return self.reply(200, path.read_bytes(), mime)
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
            payload=json.loads(raw); page=payload.get('page','index.html'); html=payload['html']; check_page(html,page)
            data=html.encode('utf8')
            with LOCK:
                target=ROOT/page; previous=target.read_bytes()
                if payload.get('version') != digest(previous): return self.reply(409, {'error':'Die Datei wurde zwischenzeitlich geändert. Speichern abgebrochen; bitte deine offenen Änderungen sichern und die Seite neu laden.'})
                folder=ROOT/'sicherungen'; folder.mkdir(exist_ok=True)
                backup=folder/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+Path(page).name)
                backup.write_bytes(previous)
                tmp=target.with_name('.'+target.name+'-editor.tmp'); tmp.write_bytes(data); os.replace(tmp,target)
                if page=='lerneinheiten/glasl.html':
                    download=ROOT/'assets/lerneinheiten/glasl/Lerntext-Glasl.txt'
                    if download.exists():
                        folder.joinpath(backup.stem+'-Lerntext.txt').write_bytes(download.read_bytes())
                        parser=LessonText(); parser.feed(html)
                        text_tmp=download.with_suffix('.txt.tmp'); text_tmp.write_text(parser.text(),encoding='utf8'); os.replace(text_tmp,download)
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
