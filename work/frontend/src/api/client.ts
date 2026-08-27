/**
 * 인증 API(auth.ts/users.ts) 공용 fetch 래퍼.
 *
 * 토큰은 여기서 localStorage에 직접 넣고 빼며(AuthContext가 로그인/로그아웃 시 호출),
 * apiFetch는 토큰이 있으면 매 요청에 Authorization 헤더를 자동으로 붙인다 — 그래서
 * api/users.ts의 함수들(getSkinProfile 등)은 토큰을 매번 인자로 안 받아도 된다.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const TOKEN_STORAGE_KEY = 'bogosara_token';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    // FastAPI 에러 응답은 {"detail": "..."} 형태 — 파싱 실패하면 상태 텍스트로 대체한다.
    const message = await res
      .json()
      .then((body) => (typeof body?.detail === 'string' ? body.detail : res.statusText))
      .catch(() => res.statusText);
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
