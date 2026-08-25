import { apiFetch } from './client';
import type { TokenRead } from './types';

export function signup(email: string, nickname: string, password: string): Promise<TokenRead> {
  return apiFetch<TokenRead>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, nickname, password }),
  });
}

export function login(email: string, password: string): Promise<TokenRead> {
  return apiFetch<TokenRead>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}
