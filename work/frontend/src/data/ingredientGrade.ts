import type { Ingredient } from './ingredientResult';

export interface IngredientBadge {
  className: string;
  label: string;
}

/**
 * 카드 뒷면(IngredientRow/IngredientDetail 공용) 배지 — 사용자에게는 내부 DB 등급명
 * (슈퍼스타/구디/기본) 대신 "핵심성분/일반성분/유의성분" 세 가지로만 보여준다(라벨은 띄어쓰기
 * 없이 붙여 쓴다 — 좁은 배지 폭에 두 글자씩 두 줄로 딱 맞는다).
 *
 * - 배합 한도/금지 등 규제 정보(restricted)가 있으면 등급과 무관하게 무조건 "유의성분"이
 *   최우선으로 뜬다 — 사용자 입장에선 이 성분이 슈퍼스타든 기본이든, 주의해야 한다는 사실이
 *   더 중요하기 때문.
 * - 나머지는 슈퍼스타 → "핵심성분", 구디/기본 → "일반성분" 두 단계로 묶는다.
 */
const CAUTION_BADGE: IngredientBadge = { className: 'ing-badge--caution', label: '유의성분' };
const STAR_BADGE: IngredientBadge = { className: 'ing-badge--star', label: '핵심성분' };
const GENERAL_BADGE: IngredientBadge = { className: 'ing-badge--good', label: '일반성분' };

export function getIngredientBadge(ingredient: Pick<Ingredient, 'display_grade' | 'restricted'>): IngredientBadge {
  if (ingredient.restricted) return CAUTION_BADGE;
  return ingredient.display_grade === 'star' ? STAR_BADGE : GENERAL_BADGE;
}
