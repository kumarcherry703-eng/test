"""Local-network remote desktop host. Start with python -m setu.server."""
import argparse
import asyncio
import hmac
import io
import os
import secrets
import socket
import time
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
SHARED = Path(os.environ.get("SETU_SHARED", "shared")).resolve()
DEMO = os.environ.get("SETU_DEMO") == "1"
PASSWORD = os.environ.get("SETU_PASSWORD") or secrets.token_urlsafe(18)
SESSIONS = set()
ATTEMPTS = {}
STARTED = time.monotonic()
app = FastAPI(title="Setu", docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

class Login(BaseModel):
    password: str = Field(max_length=200)

class Input(BaseModel):
    type: str
    x: float = 0
    y: float = 0
    button: str = 'left'
    text: str = Field(default='', max_length=1000)
    key: str = ''
    amount: int = 0


def authorize(authorization: str | None):
    if not authorization or not authorization.startswith('Bearer ') or authorization[7:] not in SESSIONS:
        raise HTTPException(401, 'Please connect first')


def check_origin(request: Request):
    origin = request.headers.get('origin')
    if origin and urlparse(origin).netloc != request.headers.get('host'):
        raise HTTPException(403, 'Origin not allowed')


def desktop():
    try:
        import pyautogui
        return pyautogui
    except Exception as exc:
        raise HTTPException(503, f'Desktop unavailable: {exc}')


def demo_image():
    image = Image.new('RGB', (1440, 900), '#e8e4df')
    d = ImageDraw.Draw(image)
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    bold = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    def f(size, is_bold=False):
        try: return ImageFont.truetype(bold if is_bold else font, size)
        except OSError: return ImageFont.load_default()
    # A clearly fictional desktop rather than a real screen capture.
    d.rectangle((0, 0, 1440, 900), fill='#ddd8d2')
    d.ellipse((880, -260, 1700, 520), fill='#c8d1bf')
    d.ellipse((-240, 500, 650, 1350), fill='#e9c5ad')
    d.rounded_rectangle((120, 70, 1320, 820), 18, fill='#faf9f6')
    d.rounded_rectangle((120, 70, 1320, 135), 18, fill='#f2f0eb')
    d.rectangle((120, 115, 1320, 135), fill='#f2f0eb')
    for x, c in [(153, '#e99988'), (176, '#e8c071'), (199, '#a9c799')]: d.ellipse((x, 95, x+12, 107), fill=c)
    d.text((626, 91), 'STUDIO SPACE', fill='#848984', font=f(14, True))
    d.rounded_rectangle((165, 183, 1275, 758), 12, fill='#ffffff', outline='#eaeae5', width=2)
    d.text((218, 236), 'Monday, October 21', fill='#989e94', font=f(17))
    d.text((218, 280), 'A little space to', fill='#273d34', font=f(51, True))
    d.text((218, 350), 'do big things.', fill='#273d34', font=f(51, True))
    d.text((220, 442), 'Your ideas, all in one place.', fill='#8b9389', font=f(21))
    d.rounded_rectangle((220, 510, 397, 560), 9, fill='#315c49')
    d.text((250, 524), 'Get started  →', fill='white', font=f(16, True))
    d.rounded_rectangle((840, 240, 1165, 605), 20, fill='#e9eee5')
    d.ellipse((887, 295, 1121, 529), fill='#c9d9c3')
    d.ellipse((937, 345, 1071, 479), fill='#789880')
    d.rounded_rectangle((505, 845, 935, 893), 17, fill='#f8f7f2')
    for i, c in enumerate(['#6c9a80', '#e8a87d', '#96aabd', '#e9ca83', '#8c9d8d', '#d6a7a0']):
        d.rounded_rectangle((530+i*67, 853, 562+i*67, 885), 7, fill=c)
    out = io.BytesIO(); image.save(out, 'JPEG', quality=78); return out.getvalue()

@app.get('/')
def index(): return FileResponse(ROOT / 'static' / 'index.html')

@app.get('/api/status')
def status():
    return {'name': socket.gethostname(), 'demo': DEMO, 'uptime': int(time.monotonic()-STARTED)}

@app.post('/api/login')
def login(body: Login, request: Request):
    check_origin(request)
    ip = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    attempts = [x for x in ATTEMPTS.get(ip, []) if now-x < 60]
    if len(attempts) >= 8: raise HTTPException(429, 'Too many attempts. Try again in a minute.')
    if not (DEMO and body.password == 'demo') and not hmac.compare_digest(body.password.encode('utf-8'), PASSWORD.encode('utf-8')):
        ATTEMPTS[ip] = attempts + [now]
        raise HTTPException(401, 'Incorrect access key')
    ATTEMPTS.pop(ip, None)
    token = secrets.token_urlsafe(32); SESSIONS.add(token)
    return {'token': token}

@app.post('/api/logout')
def logout(request: Request, authorization: str | None = Header(default=None)):
    check_origin(request); authorize(authorization); SESSIONS.discard(authorization[7:]); return {'ok': True}

@app.get('/api/screen')
def screen(authorization: str | None = Header(default=None)):
    authorize(authorization)
    if DEMO: data = demo_image()
    else:
        try:
            image = desktop().screenshot(); image.thumbnail((1920, 1080)); out = io.BytesIO(); image.save(out, 'JPEG', quality=65); data = out.getvalue()
        except HTTPException: raise
        except Exception as exc: raise HTTPException(503, f'Screen capture failed: {exc}')
    return Response(data, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})

@app.post('/api/input')
def send_input(body: Input, request: Request, authorization: str | None = Header(default=None)):
    check_origin(request); authorize(authorization)
    if body.type not in {'click', 'move', 'scroll', 'text', 'key'}: raise HTTPException(400, 'Unknown input')
    if body.type == 'text' and not body.text.isascii(): raise HTTPException(400, 'Only ASCII text is supported')
    if body.button not in {'left', 'right'}: raise HTTPException(400, 'Invalid button')
    if body.key and body.key not in {'enter','backspace','tab','esc','space','up','down','left','right','delete','home','end'}: raise HTTPException(400, 'Unsupported key')
    if DEMO: return {'ok': True}
    try:
        pg = desktop(); w, h = pg.size(); x = min(w-1, max(0, int(body.x*w))); y = min(h-1, max(0, int(body.y*h)))
        if body.type == 'click': pg.click(x, y, button=body.button)
        elif body.type == 'move': pg.moveTo(x, y)
        elif body.type == 'scroll': pg.scroll(max(-10, min(10, body.amount)))
        elif body.type == 'text': pg.write(body.text, interval=0.001)
        elif body.type == 'key' and body.key: pg.press(body.key)
    except HTTPException: raise
    except Exception as exc: raise HTTPException(503, f'Input failed: {exc}')
    return {'ok': True}

@app.get('/api/files')
def files(authorization: str | None = Header(default=None)):
    authorize(authorization); SHARED.mkdir(parents=True, exist_ok=True)
    return [{'name': p.name, 'size': p.stat().st_size} for p in sorted(SHARED.iterdir()) if p.is_file() and not p.is_symlink()]

@app.get('/api/files/{name}')
def download(name: str, authorization: str | None = Header(default=None)):
    authorize(authorization); path = SHARED / name
    if Path(name).name != name or path.is_symlink() or not path.is_file(): raise HTTPException(404, 'File not found')
    return FileResponse(path, filename=name, media_type='application/octet-stream')

@app.post('/api/files')
async def upload(request: Request, file: UploadFile = File(...), authorization: str | None = Header(default=None)):
    check_origin(request); authorize(authorization)
    name = (file.filename or '').replace('\\', '/').split('/')[-1]
    if name in {'', '.', '..'}: raise HTTPException(400, 'Invalid filename')
    SHARED.mkdir(parents=True, exist_ok=True); path = SHARED / name
    if path.exists() or path.is_symlink(): raise HTTPException(409, 'File already exists')
    size = 0
    created = False
    try:
        with path.open('xb') as output:
            created = True
            while chunk := await file.read(1024*1024):
                size += len(chunk)
                if size > 20*1024*1024: raise HTTPException(413, 'Maximum file size is 20 MB')
                output.write(chunk)
    except FileExistsError:
        raise HTTPException(409, 'File already exists')
    except Exception:
        if created: path.unlink(missing_ok=True)
        raise
    return {'name': name, 'size': size}


def main():
    parser = argparse.ArgumentParser(description='Setu local remote desktop')
    parser.add_argument('--demo', action='store_true', help='Run a simulated desktop (no real PC control)')
    parser.add_argument('--host', default='0.0.0.0'); parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    global DEMO
    DEMO = args.demo
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]; s.close()
    except OSError: ip = 'YOUR-PC-IP'
    print(f'\n  SETU  |  {"DEMO MODE" if DEMO else "REMOTE HOST"}\n  Open on your phone: http://{ip}:{args.port}\n  Access key: {"demo" if DEMO else PASSWORD}\n  Keep this key private. Use only on a trusted network.\n', flush=True)
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level='warning')

if __name__ == '__main__': main()
