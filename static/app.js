const $ = (id) => document.getElementById(id);
const state = { user: null };

async function api(path, method = 'GET', payload) {
  const res = await fetch('/api' + path, {
    method,
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function initials(name) {
  return String(name || '?')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join('');
}

function showError(id, err) {
  $(id).textContent = err ? err.message : '';
}

function showApp(loggedIn) {
  $('auth').hidden = loggedIn;
  $('app').hidden = !loggedIn;
}

async function authenticate(path) {
  showError('authError', null);

  const email = $('email').value.trim();
  const password = $('password').value;
  const name = $('name').value.trim();

  if (!email || !password) {
    showError('authError', new Error('Enter your email and password.'));
    return;
  }
  if (path === '/register') {
    if (!name) {
      showError('authError', new Error('Enter your name to register.'));
      return;
    }
    if (password.length < 6) {
      showError('authError', new Error('Password must be at least 6 characters.'));
      return;
    }
  }

  const buttons = [$('loginBtn'), $('registerBtn')];
  buttons.forEach((button) => { button.disabled = true; });

  try {
    const payload = { email, password };
    if (path === '/register') payload.name = name;

    state.user = await api(path, 'POST', payload);
    showError('authError', null);
    start();
  } catch (err) {
    showError('authError', err);
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
  }
}

function start() {
  showApp(true);
  const displayName = state.user?.name || state.user?.email || 'Signed in';
  $('who').textContent = displayName;
  $('whoAvatar').textContent = initials(displayName);
  showError('appError', null);
}

/* ---------- events ---------- */

$('loginBtn').onclick = () => authenticate('/login');
$('registerBtn').onclick = () => authenticate('/register');
$('password').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') authenticate('/login');
});

$('logoutBtn').onclick = async () => {
  try {
    await api('/logout', 'POST');
    state.user = null;
    $('password').value = '';
    showError('authError', null);
    showError('appError', null);
    showApp(false);
  } catch (err) {
    showError('appError', err);
  }
};

// If the session cookie is still valid, skip the login screen.
(async () => {
  try {
    state.user = await api('/me');
    start();
  } catch (err) {
    showApp(false);
  }
})();