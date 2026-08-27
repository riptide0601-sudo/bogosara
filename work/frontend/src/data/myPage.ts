import type { SavedResultRead } from '../api/types';

export interface SavedResult {
  /** 실제 백엔드 product_id — 클릭 시 ResultView에서 이 id로 /products/{id}를 다시 조회한다. */
  id: string;
  productName: string;
  brand: string | null;
  /** 백엔드 SavedResultRead엔 등급/주의성분 개수가 없다 — 있으면만 배지·메타로 보여준다. */
  grade?: 'star' | 'good' | 'base';
  cautionCount?: number;
  savedAt: string;
}

export interface SkinProfile {
  skinTypes: string[];
  watchedIngredients: string[];
}

/** app/skin_fit.py가 다루는 피부 타입 네 가지 (README "피부 타입별 위험/궁합 성분 탐지" 참고). */
export const SKIN_TYPE_OPTIONS = ['지성', '복합성', '건성', '민감성'];

export function toSavedResult(r: SavedResultRead): SavedResult {
  return {
    id: r.product_id,
    productName: r.product_name,
    brand: r.brand,
    savedAt: r.saved_at,
  };
}
