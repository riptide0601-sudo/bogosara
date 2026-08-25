import { apiFetch } from './client';
import type { SavedResultRead, SkinProfile, UserRead } from './types';

export function getMe(): Promise<UserRead> {
  return apiFetch<UserRead>('/users/me');
}

export function updateMe(patch: { nickname?: string; notify_alerts?: boolean }): Promise<UserRead> {
  return apiFetch<UserRead>('/users/me', { method: 'PATCH', body: JSON.stringify(patch) });
}

export function getSkinProfile(): Promise<SkinProfile> {
  return apiFetch<SkinProfile>('/users/me/skin-profile');
}

export function updateSkinProfile(patch: Partial<SkinProfile>): Promise<SkinProfile> {
  return apiFetch<SkinProfile>('/users/me/skin-profile', { method: 'PUT', body: JSON.stringify(patch) });
}

export function listSavedResults(): Promise<SavedResultRead[]> {
  return apiFetch<SavedResultRead[]>('/users/me/saved-results');
}

export function saveResult(productId: string): Promise<SavedResultRead> {
  return apiFetch<SavedResultRead>('/users/me/saved-results', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId }),
  });
}

export function unsaveResult(productId: string): Promise<void> {
  return apiFetch<void>(`/users/me/saved-results/${encodeURIComponent(productId)}`, { method: 'DELETE' });
}
