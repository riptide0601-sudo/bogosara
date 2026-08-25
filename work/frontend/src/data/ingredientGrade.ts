import type { Ingredient } from './ingredientResult';

export interface IngredientBadge {
  className: string;
  label: string;
}

/**
 * 성분 배지(등급 표시) — 사용자 용어는 핵심성분/일반성분/유의성분 세 가지만 쓴다
 * (IngredientRow/IngredientDetail이 이 함수를 공유). 규제 정보(restricted)가 있으면
 * display_grade와 무관하게 유의성분 배지가 최우선이다.
 */
export function getIngredientBadge(ingredient: Ingredient): IngredientBadge {
  if (ingredient.restricted) {
    return { className: 'ing-badge--caution', label: '유의성분' };
  }
  switch (ingredient.display_grade) {
    case 'star':
      return { className: 'ing-badge--star', label: '핵심성분' };
    case 'good':
      return { className: 'ing-badge--good', label: '일반성분' };
    default:
      return { className: '', label: '일반성분' };
  }
}
