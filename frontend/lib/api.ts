function defaultApiBase() {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) return process.env.NEXT_PUBLIC_API_BASE_URL;
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') return 'http://127.0.0.1:8005';
  }
  return '';
}

const API_BASE = defaultApiBase();

export async function readApiJson(response: Response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return {
      detail: response.ok ? "接口返回格式异常。" : `接口没有返回 JSON，状态码 ${response.status}。请确认云端后端 API 已部署并配置。`,
    };
  }
}

export function getToken() {
  if (typeof window === 'undefined') return '';
  return window.localStorage.getItem('access_token') || '';
}

export function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return {
    ...(extra || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function authFetch(path: string, init: RequestInit = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  return fetch(url, {
    ...init,
    headers: authHeaders(init.headers),
  });
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await authFetch(path, { cache: 'no-store' });
  if (!response.ok) throw new Error(`API error ${response.status}`);
  return readApiJson(response);
}

export function saveAuth(token: string, user: unknown) {
  window.localStorage.setItem('access_token', token);
  window.localStorage.setItem('current_user', JSON.stringify(user));
}

export function clearAuth() {
  window.localStorage.removeItem('access_token');
  window.localStorage.removeItem('current_user');
}

export function currentUser() {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem('current_user');
  return raw ? JSON.parse(raw) : null;
}

export { API_BASE };
