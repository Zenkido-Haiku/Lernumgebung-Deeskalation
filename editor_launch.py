"""Start the local editor from a user double-click, then open its browser page."""
import argparse, base64, hashlib, json, subprocess, sys, time, webbrowser
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parent
URL='http://127.0.0.1:8767'
def ready():
    try:
        with urlopen(URL+'/api/ping',timeout=1) as response: info=json.load(response)
        return info.get('app')=='deeskalation-editor' and info.get('root')==hashlib.sha256(str(ROOT).encode()).hexdigest()
    except Exception: return False
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    if not ready():
        executable=Path(sys.executable).with_name('pythonw.exe')
        if not executable.exists(): executable=Path(sys.executable)
        command='"'+str(executable)+'" "'+str(ROOT/'editor_server.py')+'"'
        def quote(value): return "'"+str(value).replace("'","''")+"'"
        script="$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="+quote(command)+";CurrentDirectory="+quote(ROOT)+"}; if($r.ReturnValue -ne 0){exit 1}"
        encoded=base64.b64encode(script.encode('utf-16le')).decode('ascii')
        result=subprocess.run(['powershell.exe','-NoProfile','-EncodedCommand',encoded],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
        if result.returncode: raise RuntimeError('Windows konnte den unabhaengigen Editor-Prozess nicht starten.')
        for attempt in range(30):
            if ready(): break
            time.sleep(.2)
        else: raise RuntimeError('Der lokale Editor startet nicht. Bitte .local/editor.log pruefen; Port 8767 koennte belegt sein.')
    if not args.no_browser: webbrowser.open(URL+'/editor')
    print('Lokaler Editor erreichbar: '+URL+'/editor')
if __name__=='__main__':
    try:main()
    except Exception as error:print('Startfehler: '+str(error));sys.exit(1)
