/** 백엔드 app/schemas/user.py 와 1:1 대응하는 응답 타입들. */

export interface UserRead {
  user_id: string;
  nickname: string;
  email: string;
  joined_at: string;
  notify_alerts: boolean;
  age: number | null;
  gender: string | null;
  /** 마이페이지 하단을 걸어다니는 캐릭터 3종(WalkingMascot) 중 고른 프로필 사진 — 'cosmetic' |
   * 'cream' | 'cushion', 아직 안 골랐으면 null. */
  profile_icon: string | null;
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

export interface RoutineRelationProduct {
  product_id: string;
  product_name: string;
  brand: string | null;
}

/** 서로 다른 제품에 걸쳐 있는 성분 조합 중 ingredient_relation에 등록된 시너지/악화 쌍.
 * product_a/b는 루틴에서 실제로 그 성분을 담고 있는 제품(대표 1개씩) — "악화"일 때만
 * alternatives_a/b(같은 카테고리 + 문제 성분 없는 대체 후보, 최대 2개씩)도 같이 온다. */
export interface RoutineRelationNote {
  relation_type: string; // "시너지" | "악화"
  ingredient_a: string;
  ingredient_b: string;
  message: string | null;
  product_a: RoutineRelationProduct | null;
  product_b: RoutineRelationProduct | null;
  alternatives_a: RoutineRelationProduct[];
  alternatives_b: RoutineRelationProduct[];
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
  /** 수분(휴멕턴트)/보습(옥클루시브·에몰리언트) 목적을 가진 성분 개수 — 막대바 시각화용. */
  hydration_count: number;
  occlusion_count: number;
  /** 각 개수에 실제로 잡힌 성분 이름들 — 막대 아래 어떤 성분들인지 보여줄 때 쓴다. */
  hydration_ingredients: string[];
  occlusion_ingredients: string[];
  skin_type_notes: RoutineSkinTypeNote[];
  relations: RoutineRelationNote[];
}

export interface RoutineHistoryProduct {
  product_id: string;
  product_name: string;
  brand: string | null;
}

/** "이 조합 저장하기"로 남긴 조합 스냅샷 한 건 — 이후 제품이 지워져도 headline/product_count는
 * 저장 당시 값 그대로 유지된다(app/models/routine_history.py 참고). */
export interface RoutineHistoryRead {
  history_id: string;
  headline: string;
  product_count: number;
  products: RoutineHistoryProduct[];
  saved_at: string;
}
