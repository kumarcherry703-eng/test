const $ = s => document.querySelector(s);
const icon = name => `<svg><use href="#${name}"/></svg>`;
let token = '', status = null, timer = null, currentImage = null, rightClick = false;
let toastTimer;
function toast(message) { const el = $('#toast'); el.textContent = message; el.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3000); }
function modal(html) { $('#modal-content').innerHTML = html; $('#modal').hidden = false; setTimeout(() => $('#modal input:not([type=file])')?.focus(), 30); }
function closeModal() { $('#modal').hidden = true; $('#modal-content').innerHTML = ''; }
$('#modal-close').onclick = closeModal;
$('#modal').onclick = e => { if (e.target === $('#modal')) closeModal(); };
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#modal').hidden) closeModal(); });
async function api(url, options = {}) {
  const headers = new Headers(options.headers || {}); if (token) headers.set('Authorization', `Bearer ${token}`);
  const res = await fetch(url, {...options, headers, cache:'no-store'});
  if (!res.ok) { let message = `Request failed (${res.status})`; try { message = (await res.json()).detail || message; } catch {} throw new Error(message); }
  return res;
}
function json(method, body) { return {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}; }
async function initialize() {
  try { status = await (await api('/api/status')).json(); $('#device-name').textContent = status.demo ? 'Studio desktop' : status.name; $('#host-label').textContent = status.demo ? 'DEMO HOST' : 'THIS HOST'; if (status.demo) { const result = await (await api('/api/login', json('POST', {password:'demo'}))).json(); token = result.token; connected(); } }
  catch { $('#device-status').textContent = 'Host unavailable'; toast('Could not reach the host.'); }
}
function loginDialog() {
  modal(`<div class="modal-kicker">LET'S GET CONNECTED</div><h2 id="modal-title">Your desk is waiting.</h2><p>Enter the access key shown in the terminal on your computer. Both devices should be on the same trusted network.</p>${status?.demo ? '<p><strong>Demo mode:</strong> use the access key <strong>demo</strong>. This is a simulated desktop.</p>' : ''}<form id="login-form"><label for="password">ACCESS KEY</label><input type="password" id="password" autocomplete="off" placeholder="Enter your access key" required><div class="error" id="login-error"></div><button class="primary-button" type="submit">Connect to device ${icon('arrow')}</button></form>`);
  $('#login-form').onsubmit = async e => { e.preventDefault(); const button = e.submitter; button.disabled = true; try { const result = await (await api('/api/login', json('POST', {password:$('#password').value}))).json(); token = result.token; closeModal(); connected(); } catch (err) { $('#login-error').textContent = err.message; } finally { button.disabled = false; } };
}
function connected() {
  $('#device-status').textContent = 'Connected'; $('#connection-title').textContent = status.demo ? 'You’re exploring the demo' : 'You’re connected';
  $('#connection-description').textContent = status.demo ? 'This simulated desktop does not control a real computer.' : 'Your desktop is ready. Tap the screen to click.';
  $('#connect-button').hidden = true; $('#control-bar').hidden = false; $('#demo-badge').hidden = !status.demo; loadScreen(); timer = setInterval(loadScreen, 1200); toast(status.demo ? 'Connected to the simulated desktop' : 'Connected to your computer');
}
let loading = false;
async function loadScreen() {
  if (!token || loading) return; loading = true;
  try { const blob = await (await api('/api/screen')).blob(); const url = URL.createObjectURL(blob); const img = $('#screen'); img.onload = () => { if (currentImage) URL.revokeObjectURL(currentImage); currentImage = url; img.classList.add('visible'); $('#screen-placeholder').hidden = true; }; img.src = url; }
  catch (err) { clearInterval(timer); toast(err.message); $('#device-status').textContent = 'Screen unavailable'; }
  finally { loading = false; }
}
async function disconnect() {
  clearInterval(timer); try { await api('/api/logout', {method:'POST'}); } catch {} token = ''; $('#screen').classList.remove('visible'); $('#screen').removeAttribute('src'); if (currentImage) URL.revokeObjectURL(currentImage); currentImage = null; $('#screen-placeholder').hidden = false; $('#demo-badge').hidden = true; $('#control-bar').hidden = true; $('#connect-button').hidden = false; $('#device-status').textContent = 'Ready to connect'; $('#connection-title').textContent = 'Ready when you are'; $('#connection-description').textContent = 'Connect to access your desktop from this device.'; toast('Disconnected');
}
$('#connect-button').onclick = loginDialog; $('#disconnect').onclick = disconnect;
async function sendInput(body) { if (!token) return; try { await api('/api/input', json('POST', body)); } catch (e) { toast(e.message); } }
$('#screen').addEventListener('click', e => { if (!token) return; const rect = e.currentTarget.getBoundingClientRect(); sendInput({type:'click', x:(e.clientX-rect.left)/rect.width, y:(e.clientY-rect.top)/rect.height, button:rightClick?'right':'left'}); if (rightClick) { rightClick = false; $('#right-click').classList.remove('selected'); toast('Right click sent'); } });
$('#screen').addEventListener('contextmenu', e => { e.preventDefault(); const rect = e.currentTarget.getBoundingClientRect(); sendInput({type:'click', x:(e.clientX-rect.left)/rect.width, y:(e.clientY-rect.top)/rect.height, button:'right'}); });
$('#screen').addEventListener('wheel', e => { e.preventDefault(); sendInput({type:'scroll', amount:e.deltaY > 0 ? -3 : 3}); }, {passive:false});
let touchY = null;
$('#screen').addEventListener('touchstart', e => { if (e.touches.length === 1) touchY = e.touches[0].clientY; }, {passive:true});
$('#screen').addEventListener('touchend', e => { if (touchY === null || !e.changedTouches.length) return; const delta = e.changedTouches[0].clientY - touchY; touchY = null; if (Math.abs(delta) > 30) { e.preventDefault(); sendInput({type:'scroll', amount:delta > 0 ? 3 : -3}); } }, {passive:false});
$('#right-click').onclick = () => { rightClick = !rightClick; toast(rightClick ? 'Tap the screen to right click' : 'Right click cancelled'); };
$('#keyboard-button').onclick = () => {
 modal(`<div class="modal-kicker">REMOTE INPUT</div><h2 id="modal-title">Type on your desktop.</h2><p>Send text or a special key to the active window. Text input supports standard ASCII characters.</p><form id="text-form"><label for="remote-text">TEXT TO SEND</label><input id="remote-text" type="text" placeholder="Write something…" maxlength="1000"><button class="primary-button" type="submit">Send text ${icon('arrow')}</button></form><label>SPECIAL KEYS</label><div class="key-list" style="display:flex;flex-wrap:wrap;gap:6px">${['enter','backspace','tab','esc','space','up','down','left','right','delete'].map(k=>`<button class="secondary-button" data-key="${k}">${k}</button>`).join('')}</div>`);
 $('#text-form').onsubmit = e => { e.preventDefault(); const value = $('#remote-text').value; if (value) { sendInput({type:'text', text:value}); $('#remote-text').value = ''; toast('Text sent'); } }; document.querySelectorAll('[data-key]').forEach(btn => btn.onclick = () => { sendInput({type:'key', key:btn.dataset.key}); toast(`${btn.dataset.key} sent`); });
};
$('#expand').onclick = async () => { if (!token) { loginDialog(); return; } try { if (!document.fullscreenElement) await $('#screen-wrap').requestFullscreen(); else await document.exitFullscreen(); } catch { toast('Fullscreen is not available on this browser'); } };
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function fileSize(n) { return n < 1024 ? `${n} B` : n < 1048576 ? `${(n/1024).toFixed(1)} KB` : `${(n/1048576).toFixed(1)} MB`; }
async function filesDialog() {
 if (!token) { toast('Connect to your device first'); loginDialog(); return; }
 modal(`<div class="modal-kicker">A LITTLE MORE FREEDOM</div><h2 id="modal-title">File transfer.</h2><p>Files are shared only through the host's <strong>shared</strong> folder. Uploads are limited to 20 MB.</p><label class="upload-label">${icon('upload')} Upload a file<input id="upload-file" type="file" hidden></label><div id="file-list"><p>Loading files…</p></div>`);
 $('#upload-file').onchange = async e => { const file = e.target.files[0]; if (!file) return; if (file.size > 20*1024*1024) { toast('Maximum file size is 20 MB'); return; } const form = new FormData(); form.append('file', file); try { await api('/api/files', {method:'POST',body:form}); toast('File uploaded'); filesDialog(); } catch (err) { toast(err.message); } };
 try { const files = await (await api('/api/files')).json(); if (!$('#file-list')) return; $('#file-list').innerHTML = files.length ? files.map(f => `<div class="file-row"><span>${escapeHtml(f.name)} <small>· ${fileSize(f.size)}</small></span><button data-file="${escapeHtml(f.name)}" aria-label="Download ${escapeHtml(f.name)}">${icon('download')}</button></div>`).join('') : '<p>No files here yet. Upload one to get started.</p>'; document.querySelectorAll('[data-file]').forEach(button => button.onclick = async () => { try { const blob = await (await api(`/api/files/${encodeURIComponent(button.dataset.file)}`)).blob(); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = button.dataset.file; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); } catch(e) { toast(e.message); } }); } catch(e) { if ($('#file-list')) $('#file-list').textContent = e.message; }
}
function helpDialog() { modal(`<div class="modal-kicker">HERE TO HELP</div><h2 id="modal-title">A little setup, then go.</h2><p>Setu connects your phone to the computer running the host.</p><ol class="help-list"><li>Start Setu on your computer and keep the terminal open.</li><li>Connect your phone and computer to the same trusted Wi-Fi.</li><li>Open the address shown in the terminal on your phone.</li><li>Enter the access key shown on the computer.</li></ol><p><strong>Privacy note:</strong> The local connection uses HTTP, not encryption. Do not use on public Wi-Fi or expose it to the internet. Use a trusted VPN for remote access.</p>`); }
document.querySelectorAll('[data-action]').forEach(button => button.onclick = () => { const action = button.dataset.action; if (action === 'files') filesDialog(); else if (action === 'help') helpDialog(); else if (action === 'device') $('#device-card').scrollIntoView({behavior:'smooth'}); else window.scrollTo({top:0,behavior:'smooth'}); });
initialize();
