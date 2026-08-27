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

/** "상품명 성분, 진짜 들어있나요?" 계열 묶음 한 칸(app/marketing_families.py 참고). */
export interface MatchedFamilyIngredient {
  name_kr: string;
  label_rank: number | null;
  /** 전성분표 원문(matched_text)에 있는 용량 표기 그대로(예: "29,049ppm"). 없으면 null — 지어내지 않는다. */
  dosage: string | null;
  /** "정확(어근일치)" | "정확(DB 정의문 근거)" | "유연물질(관련이지만 다른 물질)". */
  match_type: string;
  is_key_ingredient: boolean;
}

/** 계열 하나 — 마케팅 용어(상품명 또는 일반 매칭)와 이 제품에 실제로 들어있는 해당 계열 성분들. */
export interface MatchedFamily {
  name: string;
  /** true면 상품명에 이 계열 용어가 실제로 등장(1순위), false면 상품명엔 없지만 전성분에서 발견(2순위). */
  from_product_name: boolean;
  ingredients: MatchedFamilyIngredient[];
}

/** "이 성분들, 무슨 일을 하나요?" 배합목적 카운트 카드 하나(app/purpose_counts.py 참고).
 * label은 원본 purpose_name을 최소 가공(괄호만 처리)한 것 — 새 카테고리명을 짓지 않는다. */
export interface PurposeCount {
  label: string;
  count: number;
  total: number;
}

/** "피부 타입별 참고" 막대바 한 줄(app/skin_fit.py compute_skin_type_counts 참고).
 * skin_type은 "지성"/"복합성"/"건성"/"민감성" 또는 피부타입 무관 "전체"(향료 알레르겐 등). */
export interface SkinTypeCount {
  skin_type: string;
  good_count: number;
  caution_count: number;
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
  /** "피부 타입별 참고" 막대바용 — skin_score_summary(문장)와 같은 근거의 숫자 버전. */
  skin_type_counts: SkinTypeCount[];
  cautions: IngredientResultCaution[];
  /** app/similarity.py 코사인 유사도 기준 추천 제품 Top3 (PhotoPanel "이런 제품은 어때요?"). */
  recommended_products: Product[];
  /**
   * "상품명 성분, 진짜 들어있나요?" 계열 묶음 — app/marketing_families.py가 계산.
   * 근거(ingredient_family/ingredient_family_member)가 아직 지정 상품 기준이라 대상 밖
   * 제품은 항상 빈 배열(그러면 섹션 자체가 렌더링되지 않는다). 최대 3개, 상품명 용어 우선.
   */
  ingredient_families: MatchedFamily[];
  /** "이 성분들, 무슨 일을 하나요?" — app/purpose_counts.py가 계산, 지정 상품 제한 없음.
   * 배합목적 데이터가 아예 없는 경우만 빈 배열(그러면 섹션 자체를 숨긴다). */
  purpose_counts: PurposeCount[];
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
