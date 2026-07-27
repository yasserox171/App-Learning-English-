// Thin API client for the admin panel (v2 §4). Token lives in localStorage;
// every request goes through request() so 401s land back on /login.
const BASE = '/api/v1/admin-api';

export function getToken() {
  return localStorage.getItem('admin_token');
}

export function getAdmin() {
  try {
    return JSON.parse(localStorage.getItem('admin_profile') || 'null');
  } catch {
    return null;
  }
}

export function setSession(token, admin) {
  localStorage.setItem('admin_token', token);
  localStorage.setItem('admin_profile', JSON.stringify(admin));
}

export function clearSession() {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_profile');
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
  }
}

export async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (resp.status === 401) {
    clearSession();
    window.location.hash = '#/login';
    throw new ApiError(401, 'Session expired');
  }
  let data = null;
  try {
    data = resp.status === 204 ? null : await resp.json();
  } catch {
    /* non-JSON body */
  }
  if (!resp.ok) {
    throw new ApiError(resp.status, data?.detail || JSON.stringify(data));
  }
  return data;
}

export const api = {
  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: { email, password } }),
  me: () => request('/auth/me'),
  stats: () => request('/stats'),
  users: (search, page = 1) =>
    request(`/users?search=${encodeURIComponent(search)}&page=${page}`),
  userDetail: (id) => request(`/users/${id}`),
  activatePremium: (body) =>
    request('/premium/activate', { method: 'POST', body }),
  contentTree: () => request('/content/tree'),
  lesson: (id) => request(`/lessons/${id}`),
  patchLesson: (id, body) => request(`/lessons/${id}`, { method: 'PATCH', body }),
  reviewLessons: () => request('/review/lessons'),
  actLesson: (id, action) =>
    request(`/review/lessons/${id}/${action}`, { method: 'POST' }),
  reviewArticles: (filters = {}) => {
    const qs = new URLSearchParams(
      Object.entries(filters).filter(([, v]) => v)
    ).toString();
    return request(`/review/articles${qs ? `?${qs}` : ''}`);
  },
  actArticle: (id, action) =>
    request(`/review/articles/${id}/${action}`, { method: 'POST' }),
  patchArticle: (id, body) =>
    request(`/articles/${id}`, { method: 'PATCH', body }),
  questions: (level) =>
    request(`/placement-questions${level ? `?level=${level}` : ''}`),
  createQuestion: (body) =>
    request('/placement-questions', { method: 'POST', body }),
  patchQuestion: (id, body) =>
    request(`/placement-questions/${id}`, { method: 'PATCH', body }),
  deleteQuestion: (id) =>
    request(`/placement-questions/${id}`, { method: 'DELETE' }),
  admins: () => request('/admins'),
  createAdmin: (body) => request('/admins', { method: 'POST', body }),
  patchAdmin: (id, body) => request(`/admins/${id}`, { method: 'PATCH', body }),
  apiKeys: () => request('/api-keys'),
  createApiKey: (body) => request('/api-keys', { method: 'POST', body }),
  revokeApiKey: (id) => request(`/api-keys/${id}/revoke`, { method: 'POST' }),
  importLogs: () => request('/import-logs'),
};
