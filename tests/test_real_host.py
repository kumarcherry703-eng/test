from PIL import Image
from fastapi.testclient import TestClient
from setu import server

class FakeDesktop:
    def __init__(self): self.calls = []
    def size(self): return (1000, 500)
    def screenshot(self): return Image.new('RGB', (1000, 500), 'red')
    def click(self, x, y, button): self.calls.append(('click', x, y, button))
    def scroll(self, amount): self.calls.append(('scroll', amount))
    def write(self, text, interval): self.calls.append(('text', text))
    def press(self, key): self.calls.append(('key', key))

def test_real_mode_captures_and_controls(monkeypatch):
    monkeypatch.setattr(server, 'DEMO', False)
    monkeypatch.setattr(server, 'PASSWORD', 'secret')
    fake = FakeDesktop()
    monkeypatch.setattr(server, 'desktop', lambda: fake)
    server.SESSIONS.clear(); server.ATTEMPTS.clear()
    client = TestClient(server.app)
    response = client.post('/api/login', json={'password':'secret'})
    auth = {'Authorization': 'Bearer ' + response.json()['token']}
    assert client.get('/api/screen', headers=auth).content.startswith(b'\xff\xd8')
    assert client.post('/api/input', headers=auth, json={'type':'click','x':0.5,'y':0.5}).status_code == 200
    assert client.post('/api/input', headers=auth, json={'type':'scroll','amount':100}).status_code == 200
    assert client.post('/api/input', headers=auth, json={'type':'text','text':'Hello'}).status_code == 200
    assert client.post('/api/input', headers=auth, json={'type':'key','key':'enter'}).status_code == 200
    assert fake.calls == [('click',500,250,'left'), ('scroll',10), ('text','Hello'), ('key','enter')]
    assert client.post('/api/input', headers=auth, json={'type':'text','text':'నమస్తే'}).status_code == 400
