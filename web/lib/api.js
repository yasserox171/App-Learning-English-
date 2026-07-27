'use client';

// Shared API client for the web app (v2 §8) — identical Django REST surface
// used by the Flutter app. Guests get a real account automatically on first
// visit, exactly like mobile (§2.1).
const BASE = '/api/v1';
const ACCESS = 'fl_access';
const REFRESH = 'fl_refresh';

export function getAccess() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS);
}

function setTokens(data) {
  localStorage.setItem(ACCESS, data.access);
  if (data.refresh) localStorage.setItem(REFRESH, data.refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
}

export class ApiError extends Error {
  constructor(status, detail, data) {
    super(detail || `HTTP ${status}`);
    this.status = status;
    this.data = data;
  }
}

async function raw(path, { method = 'GET', body, isForm = false } = {}) {
  const headers = {};
  const token = getAccess();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json';

  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });

  let data = null;
  try {
    data = resp.status === 204 ? null : await resp.json();
  } catch {
    /* empty body */
  }
  if (!resp.ok) throw new ApiError(resp.status, data?.detail, data);
  return data;
}

/** Refresh once on 401, then retry; otherwise fall back to a fresh guest. */
async function withAuthRetry(path, options) {
  try {
    return await raw(path, options);
  } catch (err) {
    if (err.status !== 401) throw err;
    const refresh = localStorage.getItem(REFRESH);
    if (refresh) {
      try {
        const data = await raw('/auth/refresh', {
          method: 'POST',
          body: { refresh },
        });
        setTokens({ access: data.access, refresh });
        return await raw(path, options);
      } catch {
        /* fall through to guest bootstrap */
      }
    }
    clearTokens();
    await ensureSession();
    return raw(path, options);
  }
}

export function request(path, options) {
  return withAuthRetry(path, options);
}

/**
 * Guest bootstrap (§2.1): reuse the stored session, else create a guest
 * account. No user input, same JWT mechanism as registered users.
 */
export async function ensureSession() {
  if (getAccess()) {
    try {
      return await raw('/auth/me');
    } catch {
      clearTokens();
    }
  }
  const country = (
    Intl.DateTimeFormat().resolvedOptions().locale.split('-')[1] || ''
  ).toLowerCase();
  const data = await raw('/auth/guest', { method: 'POST', body: { country } });
  setTokens(data);
  return data.user;
}

export const api = {
  me: () => request('/auth/me'),
  login: async (email, password) => {
    const data = await raw('/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    setTokens(data);
    return data.user;
  },
  // Registering while holding a guest token converts that row in place.
  register: async (payload) => {
    const data = await request('/auth/register', {
      method: 'POST',
      body: payload,
    });
    setTokens(data);
    return data.user;
  },
  googleLogin: async (idToken) => {
    const data = await request('/auth/social/google', {
      method: 'POST',
      body: { id_token: idToken },
    });
    setTokens(data);
    return data.user;
  },

  feed: () => request('/news/feed'),
  article: (id) => request(`/news/${id}`),
  submitAnswer: (articleId, exerciseId, answer) =>
    request(`/news/${articleId}/exercises/${exerciseId}/submit`, {
      method: 'POST',
      body: answer,
    }),

  levels: () => request('/levels'),
  levelUnits: (levelId) => request(`/levels/${levelId}/units`),
  unitLessons: (unitId) => request(`/units/${unitId}/lessons`),
  lesson: (id) => request(`/lessons/${id}`),

  wallet: () => request('/billing/wallet'),
  redeem: (tier) =>
    request('/billing/redeem', { method: 'POST', body: { tier } }),
  plans: () => request('/billing/plans'),
  stripeCheckout: (plan) =>
    request('/billing/stripe/checkout', {
      method: 'POST',
      body: {
        plan,
        success_url: `${window.location.origin}/pay/success`,
        cancel_url: `${window.location.origin}/premium`,
      },
    }),
  cmiInitiate: (plan) =>
    request('/billing/cmi/initiate', {
      method: 'POST',
      body: {
        plan,
        ok_url: `${window.location.origin}/pay/success`,
        fail_url: `${window.location.origin}/premium`,
      },
    }),

  placementStart: () => request('/placement/start', { method: 'POST' }),
  placementAnswer: (sessionId, answers) =>
    request('/placement/answer', {
      method: 'POST',
      body: { session_id: sessionId, answers },
    }),

  tutorStart: (lessonId) =>
    request('/tutor/sessions', { method: 'POST', body: { lesson_id: lessonId } }),
  tutorTurnAudio: (sessionId, blob) => {
    const form = new FormData();
    // Safari records audio/mp4; Chrome/Firefox webm. Whisper accepts both —
    // the extension must match the container or the API rejects it.
    const ext = blob.type.includes('mp4') ? 'mp4' : 'webm';
    form.append('audio', blob, `turn.${ext}`);
    return request(`/tutor/sessions/${sessionId}/turn`, {
      method: 'POST',
      body: form,
      isForm: true,
    });
  },
  tutorTurnText: (sessionId, text) =>
    request(`/tutor/sessions/${sessionId}/turn`, {
      method: 'POST',
      body: { text },
    }),
  tutorEnd: (sessionId) =>
    request(`/tutor/sessions/${sessionId}/end`, { method: 'POST' }),
};
