// ─── Auth ─────────────────────────────────────────────────────────────────
const Auth = {
  getToken() { return localStorage.getItem('token'); },
  setToken(t) { localStorage.setItem('token', t); },
  clear() { localStorage.removeItem('token'); localStorage.removeItem('user'); },
  isLoggedIn() { return !!this.getToken(); },
  getUser() { return JSON.parse(localStorage.getItem('user') || 'null'); },
  setUser(u) { localStorage.setItem('user', JSON.stringify(u)); },
};

// ─── API fetch ────────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = Auth.getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) { logout(); return null; }
  return res;
}

function logout() {
  Auth.clear();
  window.location.href = '/login';
}

// 사용자가 명시적으로 로그아웃 클릭 시 — 감사 로그 기록 후 로그아웃
async function userLogout() {
  try {
    await apiFetch('/api/access-log', {
      method: 'POST',
      body: JSON.stringify({ path: window.location.pathname, action: 'logout' }),
    });
  } catch { /* best-effort */ }
  logout();
}

// 현재 페이지(메뉴) 접속을 감사 로그로 기록 (best-effort)
async function logAccess() {
  try {
    await apiFetch('/api/access-log', {
      method: 'POST',
      body: JSON.stringify({ path: window.location.pathname, action: 'view' }),
    });
  } catch { /* best-effort */ }
}

// ─── Sidebar toggle ───────────────────────────────────────────────────────
function initSidebar() {
  const btn = document.getElementById('sidebarToggle');
  if (!btn) return;

  // 저장된 접힘 상태 복원
  if (localStorage.getItem('sidebarCollapsed') === '1') {
    document.body.classList.add('sidebar-collapsed');
  }

  btn.addEventListener('click', () => {
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    localStorage.setItem('sidebarCollapsed', collapsed ? '1' : '0');
  });
}

// ─── Accordion toggle ─────────────────────────────────────────────────────
function toggleGroup(id) {
  const grp = document.getElementById(id);
  if (!grp) return;
  const isOpen = grp.classList.toggle('open');
  localStorage.setItem('menu_' + id, isOpen ? '1' : '0');
}

function restoreAccordionStates() {
  const groups = ['grp-data', 'grp-analysis', 'grp-models', 'grp-resource', 'grp-mgmt'];
  groups.forEach(id => {
    const grp = document.getElementById(id);
    if (!grp) return;
    const saved = localStorage.getItem('menu_' + id);
    if (saved !== null) {
      const isOpen = saved === '1';
      grp.classList.toggle('open', isOpen);
    }
  });
}

// ─── Admin 메뉴 표시 ─────────────────────────────────────────────────────
function initAdminMenu() {
  const user = Auth.getUser();
  if (user && user.role === 'admin') {
    ['grp-resource', 'grp-mgmt'].forEach(id => {
      const grp = document.getElementById(id);
      if (grp) grp.style.display = '';
    });
  }
}

// ─── Feature Permissions ─────────────────────────────────────────────────
window._myPermissions = null;

async function loadMyPermissions() {
  if (window._myPermissions !== null) return window._myPermissions;
  try {
    const res = await apiFetch('/api/auth/me/permissions');
    window._myPermissions = (res && res.ok) ? await res.json() : [];
  } catch {
    window._myPermissions = [];
  }
  return window._myPermissions;
}

function hasPermission(feature) {
  return (window._myPermissions || []).includes(feature);
}

// ─── 비밀번호 변경 ─────────────────────────────────────────────────────────
function openChangePwModal(forced = false) {
  const modal = document.getElementById('changePwModal');
  if (!modal) return;
  ['cp-current', 'cp-new', 'cp-confirm'].forEach(id => {
    const e = document.getElementById(id); if (e) e.value = '';
  });
  const forcedBox = document.getElementById('changePwForced');
  const cancelBtn = document.getElementById('cp-cancel');
  if (forcedBox) forcedBox.style.display = forced ? 'block' : 'none';
  if (cancelBtn) cancelBtn.style.display = forced ? 'none' : '';
  modal.dataset.forced = forced ? '1' : '0';
  modal.classList.add('open');
}

function closeChangePwModal() {
  const modal = document.getElementById('changePwModal');
  if (!modal || modal.dataset.forced === '1') return;  // 강제 모드는 닫기 불가
  modal.classList.remove('open');
}

async function submitChangePassword() {
  const cur = document.getElementById('cp-current').value;
  const nw  = document.getElementById('cp-new').value;
  const cf  = document.getElementById('cp-confirm').value;
  if (!cur || !nw) { alert('현재 비밀번호와 새 비밀번호를 입력하세요.'); return; }
  if (nw !== cf) { alert('새 비밀번호 확인이 일치하지 않습니다.'); return; }

  const res = await apiFetch('/api/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: cur, new_password: nw }),
  });
  if (!res) return;
  if (res.ok) {
    const u = Auth.getUser();
    if (u) { u.must_change_password = false; Auth.setUser(u); }
    const modal = document.getElementById('changePwModal');
    if (modal) { modal.dataset.forced = '0'; modal.classList.remove('open'); }
    alert('비밀번호가 변경되었습니다.');
  } else {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || '비밀번호 변경에 실패했습니다.');
  }
}

// ─── DOMContentLoaded ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (window.location.pathname === '/login') return;

  if (!Auth.isLoggedIn()) {
    window.location.href = '/login';
    return;
  }

  const user = Auth.getUser();
  const el = document.getElementById('nav-username');
  if (el && user) el.textContent = user.name || user.username;

  initSidebar();
  restoreAccordionStates();
  initAdminMenu();
  logAccess();

  // 초기화/최초발급 후 비밀번호 변경 강제
  if (user && user.must_change_password) {
    openChangePwModal(true);
  }
});
