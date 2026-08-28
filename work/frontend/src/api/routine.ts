import { apiFetch } from './client';
import type { RoutineAnalysis, RoutineHistoryRead, RoutineItemRead } from './types';

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

/** "초기화" — 등록한 화장품을 한꺼번에 지운다. 별도 벌크 삭제 엔드포인트가 없어서
 * 개별 삭제(removeFromRoutine)를 병렬로 호출한다. */
export function clearRoutine(productIds: string[]): Promise<void[]> {
  return Promise.all(productIds.map((id) => removeFromRoutine(id)));
}

export function getRoutineAnalysis(): Promise<RoutineAnalysis> {
  return apiFetch<RoutineAnalysis>('/users/me/routine/analysis');
}

export function listRoutineHistory(): Promise<RoutineHistoryRead[]> {
  return apiFetch<RoutineHistoryRead[]>('/users/me/routine/history');
}

export function saveRoutineHistory(): Promise<RoutineHistoryRead> {
  return apiFetch<RoutineHistoryRead>('/users/me/routine/history', { method: 'POST' });
}

export function deleteRoutineHistory(historyId: string): Promise<void> {
  return apiFetch<void>(`/users/me/routine/history/${encodeURIComponent(historyId)}`, {
    method: 'DELETE',
  });
}

/** 저장된 조합 기록 하나를 그때 제품 구성 그대로 다시 분석한 결과 — "조합 기록" 카드 클릭 시. */
export function getRoutineHistoryAnalysis(historyId: string): Promise<RoutineAnalysis> {
  return apiFetch<RoutineAnalysis>(`/users/me/routine/history/${encodeURIComponent(historyId)}/analysis`);
}
