import { apiFetch } from './client';
import type { RoutineAnalysis, RoutineItemRead } from './types';

export function listRoutine(): Promise<RoutineItemRead[]> {
  return apiFetch<RoutineItemRead[]>('/users/me/routine');
}

export function addToRoutine(productId: string): Promise<RoutineItemRead> {
  return apiFetch<RoutineItemRead>('/users/me/routine', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId }),
  });
}

export function removeFromRoutine(productId: string): Promise<void> {
  return apiFetch<void>(`/users/me/routine/${encodeURIComponent(productId)}`, { method: 'DELETE' });
}

export function getRoutineAnalysis(): Promise<RoutineAnalysis> {
  return apiFetch<RoutineAnalysis>('/users/me/routine/analysis');
}
