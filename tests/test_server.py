import io
from fastapi.testclient import TestClient
from setu import server

client = TestClient(server.app)

def setup_function():
    server.DEMO = True
    server.SESSIONS.clear()
    server.ATTEMPTS.clear()

def login():
    r = client.post('/api/login', json={'password': 'demo'})
    assert r.status_code == 200
    return {'Authorization': 'Bearer ' + r.json()['token']}

def test_auth_and_demo_screen():
    assert client.get('/api/screen').status_code == 401
    assert client.post('/api/login', json={'password':'wrong'}).status_code == 401
    headers = login()
    screen = client.get('/api/screen', headers=headers)
    assert screen.status_code == 200 and screen.headers['content-type'] == 'image/jpeg'
    assert client.post('/api/input', json={'type':'click','x':0.5,'y':0.5}, headers=headers).status_code == 200
    assert client.post('/api/input', json={'type':'bad'}, headers=headers).status_code == 400
    assert client.post('/api/logout', headers=headers).status_code == 200
    assert client.get('/api/screen', headers=headers).status_code == 401

def test_origin_and_rate_limit():
    assert client.post('/api/login', json={'password':'demo'}, headers={'Origin':'https://evil.example'}).status_code == 403
    for _ in range(8): assert client.post('/api/login', json={'password':'wrong'}).status_code == 401
    assert client.post('/api/login', json={'password':'demo'}).status_code == 429

def test_files_are_scoped_and_no_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'SHARED', tmp_path)
    headers = login()
    assert client.post('/api/files', files={'file':('hello.txt', io.BytesIO(b'hello'))}, headers=headers).status_code == 200
    assert client.post('/api/files', files={'file':('hello.txt', io.BytesIO(b'bye'))}, headers=headers).status_code == 409
    assert client.get('/api/files', headers=headers).json() == [{'name':'hello.txt','size':5}]
    assert client.get('/api/files/hello.txt', headers=headers).content == b'hello'
    assert client.get('/api/files/hello.txt').status_code == 401
