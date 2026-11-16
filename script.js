const $ = (id) => document.getElementById(id);
let mode = 'login';
let generatedContent = '';

function setMessage(id, message, success = false) {
  const el = $(id); el.textContent = message; el.style.color = success ? '#16816e' : '#bd5148';
}
function showApp(name) {
  $('authView').hidden = true; $('appView').hidden = false; $('userName').textContent = name || 'User';
}
function showAuth() { $('appView').hidden = true; $('authView').hidden = false; }
function setMode(next) {
  mode = next;
  const signup = mode === 'register';
  $('nameField').hidden = !signup;
  $('authTitle').textContent = signup ? 'Create your account' : 'Sign in to your workspace';
  $('authSubtitle').textContent = signup ? 'Set up your private medical content studio.' : 'Access your medical content studio.';
  $('authSubmit').innerHTML = signup ? 'Create account <span>→</span>' : 'Sign in <span>→</span>';
  $('switchText').textContent = signup ? 'Already have an account?' : 'New to MedContent AI?';
  $('switchMode').textContent = signup ? 'Sign in' : 'Create an account';
  $('password').autocomplete = signup ? 'new-password' : 'current-password';
  setMessage('authMessage', '');
}
$('switchMode').addEventListener('click', () => setMode(mode === 'login' ? 'register' : 'login'));
$('authForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = { email: $('email').value.trim(), password: $('password').value };
  if (mode === 'register') payload.name = $('name').value.trim();
  const button = $('authSubmit'); button.disabled = true; button.textContent = 'Please wait...';
  try {
    const response = await fetch(`/api/${mode}`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Authentication failed.');
    showApp(data.name);
  } catch (err) { setMessage('authMessage', err.message); }
  finally { button.disabled = false; $('authSubmit').innerHTML = mode === 'register' ? 'Create account <span>→</span>' : 'Sign in <span>→</span>'; }
});
$('logoutBtn').addEventListener('click', async () => {
  await fetch('/api/logout', {method:'POST'}); generatedContent = ''; showAuth(); $('authForm').reset(); setMode('login');
});
$('topic').addEventListener('input', () => $('charCount').textContent = `${$('topic').value.length} / 1500`);
$('generatorForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const button = $('generateBtn'); button.disabled = true; button.textContent = '✦ Generating your content...';
  setMessage('generateMessage', '');
  $('result').textContent = 'Preparing your medical content...';
  $('copyBtn').disabled = true; $('downloadBtn').disabled = true;
  try {
    const response = await fetch('/api/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({topic:$('topic').value.trim(), content_type:$('contentType').value, audience:$('audience').value, tone:$('tone').value})});
    const data = await response.json();
    if (response.status === 401) { showAuth(); throw new Error('Your session expired. Please sign in again.'); }
    if (!response.ok) throw new Error(data.error || 'Generation failed.');
    generatedContent = data.content || ''; $('result').textContent = generatedContent;
    $('copyBtn').disabled = !generatedContent; $('downloadBtn').disabled = !generatedContent;
    setMessage('generateMessage', 'Your medical content is ready.', true);
  } catch (err) { $('result').textContent = 'Your content could not be generated.'; setMessage('generateMessage', err.message); }
  finally { button.disabled = false; button.innerHTML = '✦ &nbsp; Generate medical content <span>→</span>'; }
});
$('copyBtn').addEventListener('click', async () => { if (!generatedContent) return; await navigator.clipboard.writeText(generatedContent); setMessage('generateMessage', 'Content copied to clipboard.', true); });
$('downloadBtn').addEventListener('click', () => { if (!generatedContent) return; const blob = new Blob([generatedContent], {type:'text/plain;charset=utf-8'}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href=url; a.download='medcontent-draft.txt'; a.click(); URL.revokeObjectURL(url); });
(async function checkSession(){ try { const r = await fetch('/api/me'); const d = await r.json(); if (d.logged_in) showApp(d.name); else showAuth(); } catch { showAuth(); } })();
