const $ = (id) => document.getElementById(id);
const STATUSES = ['To Do', 'In Progress', 'In Review', 'Done'];
const state = { user: null, projects: [], projectId: null };

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

// Use textContent rather than innerHTML to avoid treating user input as HTML.
function el(tag, text, cls) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (cls) element.className = cls;
  return element;
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

function fillSelect(select, options, selected) {
  select.replaceChildren();
  options.forEach(([value, label]) => {
    const option = el('option', label);
    option.value = value;
    select.appendChild(option);
  });
  if (selected !== undefined) select.value = String(selected);
}

/* ---------- auth ---------- */

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
    await start();
  } catch (err) {
    showError('authError', err);
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
  }
}

async function start() {
  showApp(true);
  const displayName = state.user?.name || state.user?.email || 'Signed in';
  $('who').textContent = displayName;
  $('whoAvatar').textContent = initials(displayName);
  showError('appError', null);
  await loadProjects();
}

/* ---------- projects (TB-16) ---------- */

function renderSidebar() {
  const project = state.projects.find((p) => Number(p.id) === Number(state.projectId));
  $('projectKey').textContent = project ? project.key : '--';
  $('projectName').textContent = project ? project.name : 'No project';
}

async function loadProjects() {
  try {
    state.projects = await api('/projects');

    if (!state.projects.length) {
      state.projectId = null;
      $('board').replaceChildren();
      fillSelect($('projectSelect'), [['', 'No projects yet']]);
      renderSidebar();
      showError('appError', null);
      return;
    }

    // Keep the selected project when possible; otherwise select the first project.
    if (!state.projects.some((project) => Number(project.id) === Number(state.projectId))) {
      state.projectId = state.projects[0].id;
    }

    fillSelect(
      $('projectSelect'),
      state.projects.map((project) => [project.id, `${project.key} - ${project.name}`]),
      state.projectId
    );
    renderSidebar();
    await loadBoard();
  } catch (err) {
    showError('appError', err);
  }
}

async function newProject() {
  const key = prompt('Project key (2-10 letters, for example TB)');
  if (!key) return;
  const cleanKey = key.trim().toUpperCase();
  if (!/^[A-Z]{2,10}$/.test(cleanKey)) {
    showError('appError', new Error('Project key must contain 2-10 letters.'));
    return;
  }

  const name = prompt('Project name');
  if (!name || !name.trim()) return;

  try {
    const project = await api('/projects', 'POST', { key: cleanKey, name: name.trim() });
    state.projectId = project.id;
    await loadProjects();
  } catch (err) {
    showError('appError', err);
  }
}
/* ---------- kanban board ---------- */

function card(issue) {
  const type = String(issue.type || 'Task');
  const priority = String(issue.priority || 'Medium');
  const cardElement = el('div', undefined, 'card');

  const tags = el('div', undefined, 'tags');
  tags.appendChild(el('span', type, 'pill type-' + type.toLowerCase()));
  tags.appendChild(el('span', priority, 'pill prio-' + priority.toLowerCase()));
  if (issue.story_points) tags.appendChild(el('span', `${issue.story_points} pts`, 'pill pts'));
  cardElement.appendChild(tags);

  cardElement.appendChild(el('h4', issue.title, 'card-title'));
  cardElement.appendChild(el('div', issue.key, 'card-key'));

  const assigneeRow = el('div', undefined, 'card-assignee');
  if (issue.assignee) {
    assigneeRow.appendChild(el('span', initials(issue.assignee), 'avatar'));
    assigneeRow.appendChild(el('span', issue.assignee));
  } else {
    assigneeRow.appendChild(el('span', '?', 'avatar none'));
    assigneeRow.appendChild(el('span', 'Unassigned'));
  }
    cardElement.appendChild(assigneeRow);

  // Status dropdown (TB-22)
  const actions = el('div', undefined, 'card-actions');
  const statusSelect = el('select');
  statusSelect.setAttribute('aria-label', `Status for ${issue.key}`);
  STATUSES.forEach((status) => {
    const option = el('option', status);
    option.value = status;
    statusSelect.appendChild(option);
  });
  statusSelect.value = issue.status;
  statusSelect.onchange = () => changeStatus(issue, statusSelect);
  actions.appendChild(statusSelect);
  
  const editButton = el('button', 'Edit', 'secondary small');
  editButton.onclick = () => openEdit(issue);
  actions.appendChild(editButton);

  const deleteButton = el('button', 'Delete', 'danger small');
  deleteButton.onclick = () => deleteIssue(issue);
  actions.appendChild(deleteButton);
  cardElement.appendChild(actions);

  return cardElement;
}

async function changeStatus(issue, select) {
  select.disabled = true;
  try {
    await api('/issues/' + issue.id, 'PATCH', { status: select.value });
    await loadBoard();
  } catch (err) {
    // Redraw first so the card goes back to its real column, then show the error
    // (loadBoard clears the error line when it succeeds).
    await loadBoard();
    showError('appError', err);
  }
}

async function loadBoard() {
  const board = $('board');
  if (!state.projectId) {
    board.replaceChildren();
    return;
  }

  const requestedId = state.projectId;
  try {
    const issues = await api(`/projects/${requestedId}/issues`);
    // Ignore a slow response if the user already switched to another project.
    if (requestedId !== state.projectId) return;

    board.replaceChildren();
    STATUSES.forEach((status) => {
      const column = el('div', undefined, 'column');
      const list = issues.filter((issue) => issue.status === status);

      const head = el('div', undefined, 'column-head');
      head.appendChild(el('h3', status));
      head.appendChild(el('span', String(list.length), 'count'));
      column.appendChild(head);

      if (!list.length) column.appendChild(el('div', 'No issues', 'empty'));
      list.forEach((issue) => column.appendChild(card(issue)));
      board.appendChild(column);
    });
    showError('appError', null);
  } catch (err) {
    showError('appError', err);
  }
}

/* ---------- edit and delete issue (TB-18) ---------- */

let editingIssue = null;

async function openEdit(issue) {
  showError('editError', null);

  // The assignee list comes from the API. If it fails we stop here, because
  // saving with an empty list would silently unassign the issue.
  let users;
  try {
    users = await api('/users');
  } catch (err) {
    showError('appError', err);
    return;
  }

  editingIssue = issue;
  $('editHeading').textContent = `Edit ${issue.key}`;
  $('editTitle').value = issue.title;
  $('editType').value = issue.type;
  $('editPriority').value = issue.priority;
  $('editPoints').value = issue.story_points ? String(issue.story_points) : '';

  fillSelect($('editAssignee'), [['', 'Unassigned'], ...users.map((user) => [user.id, user.name])]);
  const currentId = issue.assignee_id ?? users.find((user) => user.name === issue.assignee)?.id;
  $('editAssignee').value = currentId ? String(currentId) : '';

  $('editDialog').showModal();
  $('editTitle').focus();
}

async function saveEdit() {
  if (!editingIssue) return;
  showError('editError', null);

  const title = $('editTitle').value.trim();
  if (!title) {
    showError('editError', new Error('Enter an issue title.'));
    return;
  }

  const points = $('editPoints').value;
  const assignee = $('editAssignee').value;
  const payload = {
    title,
    type: $('editType').value,
    priority: $('editPriority').value,
    story_points: points ? Number(points) : null,
    assignee_id: assignee ? Number(assignee) : null,
  };

  $('editSaveBtn').disabled = true;
  try {
    await api('/issues/' + editingIssue.id, 'PATCH', payload);
    $('editDialog').close();
    await loadBoard();
  } catch (err) {
    // Keep the dialog open so the person can fix the value.
    showError('editError', err);
  } finally {
    $('editSaveBtn').disabled = false;
  }
}

async function deleteIssue(issue) {
  if (!confirm(`Delete ${issue.key}: ${issue.title}?\n\nThis cannot be undone.`)) return;
  try {
    await api('/issues/' + issue.id, 'DELETE');
    await loadBoard();
  } catch (err) {
    // Redraw first, then show the error (loadBoard clears the error line when it succeeds).
    await loadBoard();
    showError('appError', err);
  }
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
    state.projects = [];
    state.projectId = null;
    $('password').value = '';
    showError('authError', null);
    showError('appError', null);
    showApp(false);
  } catch (err) {
    showError('appError', err);
  }
};

$('projectSelect').onchange = (event) => {
  const selectedId = event.target.value;
  state.projectId = selectedId ? Number(selectedId) : null;
  renderSidebar();
  loadBoard();
};
$('newProjectBtn').onclick = newProject;

$('editSaveBtn').onclick = saveEdit;
$('editCancelBtn').onclick = () => $('editDialog').close();
$('editTitle').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') saveEdit();
});
$('editDialog').addEventListener('close', () => { editingIssue = null; });

// If the session cookie is still valid, skip the login screen.
(async () => {
  try {
    state.user = await api('/me');
    await start();
  } catch (err) {
    showApp(false);
  }
})();