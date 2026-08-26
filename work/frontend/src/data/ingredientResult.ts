import { loadIngredientResultFromApi } from '../api';
import type { Product } from './mockProducts';

export type IngredientGrade = 'star' | 'good' | 'base';

export interface IngredientPurpose {
  name: string;
  description: string;
}

export interface IngredientRelation {
  relation_type: string;
  user_message: string;
  related_ingredient_name: string;
}

export interface IngredientLlmSummary {
  summary_text: string;
  benefit_text: string;
  caution_text: string;
  usage_reason_text: string;
  caution_group_text: string;
  combo_recommendation: string;
}

/** 배합 한도/금지 성분 등 규제 정보 — 현재 백엔드 DB엔 아직 데이터가 없어 항상 null (api.ts 참고). */
export interface IngredientRestriction {
  regulate_type: string;
  limit_cond: string;
}

export interface Ingredient {
  /** GET /products/{id}/ingredients/{ingredient_id}/family-rank 호출에 필요한 DB PK. */
  ingredient_id: number;
  name_kr: string;
  name_en: string;
  /** DB 등급이 아니라 프론트에서 임시로 매기는 표시 등급 — api.ts의 toIngredient() 참고. */
  display_grade: IngredientGrade;
  label_rank: number;
  safety_level: string;
  purposes: IngredientPurpose[];
  restricted: IngredientRestriction | null;
  relations: IngredientRelation[];
  llm_summary: IngredientLlmSummary;
}

export interface IngredientResultKeyIngredient {
  name: string;
  purpose: string;
}

export interface IngredientResultCaution {
  name: string;
  reason: string;
}

export interface IngredientResultProduct {
  /** 검색 진입(source==='search')에서만 실재 — 계열 비교(family-rank) API 호출에 쓰인다.
   * 스캔 진입은 DB product가 없어 null (data/ingredientResult.ts의 loadIngredientResult 참고). */
  product_id: string | null;
  product_name: string;
  raw_ingredients: string;
  summary: string;
  key_ingredients: IngredientResultKeyIngredient[];
  ingredient_explanation: string;
  /** api.ts toAbsoluteImageUrl()이 백엔드 origin을 붙인 절대 URL — 없으면 null(PhotoPanel이 플레이스홀더로 대체). */
  image_url: string | null;
  category_description: string;
  /** app/schemas/product.py computed_field — 제품명 기반 올리브영 검색 결과 페이지 링크. */
  oliveyoung_url: string;
  skin_score_summary: string;
  cautions: IngredientResultCaution[];
  /** app/similarity.py 코사인 유사도 기준 추천 제품 Top3 (PhotoPanel "이런 제품은 어때요?"). */
  recommended_products: Product[];
}

export interface IngredientResult {
  product: IngredientResultProduct;
  ingredients: Ingredient[];
}

export type IngredientResultRequest =
  | { source: 'search'; productId: string; productName: string }
  | { source: 'scan'; imageDataUrl: string };

/** ResultView가 쓰는 단일 진입점 — 실제 로딩 로직(API 호출)은 api.ts에 있다. */
export function loadIngredientResult(request: IngredientResultRequest): Promise<IngredientResult> {
  return loadIngredientResultFromApi(request);
}
