/** 백엔드 app/schemas/user.py 와 1:1 대응하는 응답 타입들. */

export interface UserRead {
  user_id: string;
  nickname: string;
  email: string;
  joined_at: string;
  notify_alerts: boolean;
}

export interface TokenRead {
  access_token: string;
  token_type: string;
  user: UserRead;
}

export interface SkinProfile {
  skin_types: string[];
  watched_ingredients: string[];
}

export interface SavedResultRead {
  product_id: string;
  product_name: string;
  brand: string | null;
  category: string | null;
  saved_at: string;
}

/** app/schemas/routine.py 와 1:1. "내 화장품 조합"에 등록한 제품 한 건. */
export interface RoutineItemRead {
  product_id: string;
  product_name: string;
  brand: string | null;
  category: string | null;
  added_at: string;
  /** product.summary(LLM 요약)가 있으면 그대로, 없으면 빈 문자열. */
  description: string;
  key_ingredients: string[];
  key_purposes: string[];
}

export interface RoutineIngredientNote {
  ingredient_id: number;
  name_kr: string | null;
  /** 성분 자체에 대한 일반 설명(항상 보임). */
  description: string | null;
  risk_type: string | null;
  /** 이 피부타입에 왜 위험/궁합인지에 대한 설명 — 호버 툴팁으로만 보여준다. */
  reason: string | null;
}

export interface RoutineSkinTypeNote {
  skin_type: string;
  risk_ingredients: RoutineIngredientNote[];
  good_ingredients: RoutineIngredientNote[];
}

/** 서로 다른 제품에 걸쳐 있는 성분 조합 중 ingredient_relation에 등록된 시너지/악화 쌍. */
export interface RoutineRelationNote {
  relation_type: string; // "시너지" | "악화"
  ingredient_a: string;
  ingredient_b: string;
  message: string | null;
}

/** app/routine_analysis.py의 분석 결과 — 루틴 전체 전성분 기준 수분/보습 판정 +
 * 유저 피부 타입 기준 위험/궁합 성분. */
export interface RoutineAnalysis {
  product_count: number;
  ingredient_count: number;
  headline: string;
  /** 루틴 전체 제품들의 key_purposes를 모아 만든, 조합 전체에 대한 한 단락 설명. */
  overall_description: string;
  hydration_note: string;
  skin_type_notes: RoutineSkinTypeNote[];
  relations: RoutineRelationNote[];
}
