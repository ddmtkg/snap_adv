"""Exercise the installed release app on a disposable Windows CI desktop."""
import ctypes
import base64
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import urllib.request

if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
    raise SystemExit('Run this test only on a disposable Windows GitHub Actions runner.')

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
snap_dir = Path.home() / '.snap'
inbox = snap_dir / 'inbox'
log_path = snap_dir / 'snap.log'
install_dir = Path(os.environ['RUNNER_TEMP']) / 'SnapSmoke'
installer = next(Path('app/src-tauri/target/release/bundle/nsis').glob('*.exe'))


def log():
    return log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''


def wait_for(predicate, label, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.2)
    diagnostics()
    raise AssertionError(f'Timed out: {label}\n{log()}')


def diagnostics():
    """Inspect only this test app's renderer; debugging is enabled only in CI."""
    out = Path('smoke-diagnostics')
    out.mkdir(exist_ok=True)
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(user32.GetForegroundWindow(), title, len(title))
    print(f'Foreground window: {title.value}', flush=True)
    try:
        from websockets.sync.client import connect
        pages = json.load(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5))
        page = next(p for p in pages if 'tauri.localhost' in p.get('url', ''))
        with connect(page['webSocketDebuggerUrl']) as ws:
            for number, method, params in [
                (1, 'Runtime.evaluate', {'expression': "JSON.stringify({active:document.activeElement?.outerHTML,input:document.querySelector('#text-input')?.outerHTML,toolbar:document.querySelector('#toolbar')?.outerHTML,focus:document.hasFocus(),atPoint:document.elementFromPoint(200,340)?.tagName})", 'returnByValue': True}),
                (2, 'Page.captureScreenshot', {}),
            ]:
                ws.send(json.dumps({'id': number, 'method': method, 'params': params}))
                while True:
                    result = json.loads(ws.recv(timeout=10))
                    if result.get('id') == number:
                        break
                if number == 1:
                    (out / 'renderer.json').write_text(json.dumps(result), encoding='utf-8')
                    print(json.dumps(result), flush=True)
                elif 'data' in result.get('result', {}):
                    (out / 'overlay.png').write_bytes(base64.b64decode(result['result']['data']))
    except Exception as exc:
        print(f'Renderer diagnostics unavailable: {exc}', flush=True)


def keys(*codes):
    for code in codes:
        user32.keybd_event(code, 0, 0, 0)
    time.sleep(0.1)
    for code in reversed(codes):
        user32.keybd_event(code, 0, 2, 0)
    time.sleep(0.2)


def click(x, y):
    user32.SetCursorPos(x, y)
    user32.mouse_event(2, 0, 0, 0, 0)
    time.sleep(0.1)
    user32.mouse_event(4, 0, 0, 0, 0)
    time.sleep(0.2)


def drag(x1, y1, x2, y2):
    user32.SetCursorPos(x1, y1)
    user32.mouse_event(2, 0, 0, 0, 0)
    for i in range(1, 11):
        user32.SetCursorPos(x1 + (x2-x1)*i//10, y1 + (y2-y1)*i//10)
        time.sleep(0.03)
    user32.mouse_event(4, 0, 0, 0, 0)
    time.sleep(0.3)


def capture():
    count = log().count('first frame:')
    keys(0x11, 0x10, 0x53)  # Ctrl+Shift+S
    wait_for(lambda: log().count('first frame:') > count, 'overlay first frame')
    time.sleep(0.5)


def files():
    return sorted(inbox.glob('snap-*.json'))


def save():
    count = len(files())
    closed = log().count('overlay closed')
    keys(0x0D)
    wait_for(lambda: len(files()) == count + 1, 'saved annotation')
    wait_for(lambda: log().count('overlay closed') > closed, 'overlay closed')
    time.sleep(0.5)
    path = files()[-1]
    metadata = json.loads(path.read_text(encoding='utf-8'))
    png = path.with_suffix('.png').read_bytes()
    assert png[:8] == b'\x89PNG\r\n\x1a\n', 'Invalid PNG signature'
    assert list(struct.unpack('>II', png[16:24])) == metadata['image_size']
    assert metadata['source']['session_type'] == 'windows'
    return metadata


process = None
try:
    subprocess.run([str(installer.resolve()), '/S', f'/D={install_dir}'], check=True, timeout=120)
    executable = install_dir / 'snap.exe'
    assert executable.is_file(), f'Installer did not create {executable}'
    print('PASS: NSIS installation', flush=True)
    test_env = dict(os.environ, WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS='--remote-debugging-port=9222')
    process = subprocess.Popen([str(executable)], env=test_env)
    wait_for(lambda: 'snap ready' in log(), 'tray startup')
    assert process.poll() is None, 'Tray process exited unexpectedly'
    print('PASS: tray startup and hotkey registration', flush=True)

    capture()
    drag(100, 150, 600, 450)
    keys(0x52)  # Rectangle
    drag(180, 220, 320, 300)
    keys(0x54)  # Text
    click(200, 340)
    for letter in 'SNAP TEST':
        keys(ord(letter))
    keys(0x0D)  # Commit text
    metadata = save()
    assert metadata['source']['crop'] is not None, metadata
    assert {a['type'] for a in metadata['annotations']} == {'rect', 'text'}, metadata
    assert any(a.get('content', '').lower() == 'snap test' for a in metadata['annotations'])
    assert metadata['image_size'][0] < metadata['source']['capture_size'][0]
    print('PASS: hotkey, capture, region crop, rectangle, text, PNG + JSON save', flush=True)

    capture()
    metadata = save()
    assert metadata['source']['crop'] is None
    assert metadata['annotations'] == []
    assert metadata['image_size'] == metadata['source']['capture_size']
    print('PASS: second capture and full-screen save from memory', flush=True)

    capture()
    count = len(files())
    closed = log().count('overlay closed')
    keys(0x1B)  # Escape
    wait_for(lambda: log().count('overlay closed') > closed, 'cancel overlay')
    assert len(files()) == count, 'Cancel unexpectedly saved a screenshot'
    assert not (Path(os.environ['TEMP']) / 'snap-capture.png').exists()
    print('PASS: cancel and no temporary full-screen PNG', flush=True)
finally:
    if process is not None and process.poll() is None:
        process.terminate()
        process.wait(timeout=15)
    print(log(), flush=True)
