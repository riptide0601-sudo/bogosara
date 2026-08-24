/**
 * 성분 결과 화면(ResultView)의 데이터 계약.
 *
 * 검색 리스트 클릭과 스캔 OCR 성공 두 진입점 모두 최종적으로 이 모양(IngredientResult)의
 * 데이터에 도달한다 — 화면 컴포넌트는 어느 경로로 왔는지 몰라도 되게 하기 위함.
 *
 * 파이프라인: OCR(전성분표 인식) → DB 매칭(성분별 슈퍼스타/구디/기본 등급·배합목적·규제정보 확정)
 * → LLM 요약(아래 summary/key_ingredients/ingredient_explanation/cautions 생성) → 카드 앞면 출력.
 * LLM에게 실제로 보내는 프롬프트와 출력 스키마는 `docs/LLM_PROMPT.md` 참고 — 이 파일의
 * `KeyIngredient`/`Caution`은 그 스키마와 1:1로 대응한다.
 *
 * `ingredients` 배열(성분별 등급·배합목적·규제정보)은 OCR→DB 매칭 결과 그대로이며 LLM이
 * 건드리지 않는 사실 데이터다 — 카드 뒷면(IngredientList/IngredientDetail)이 이 배열 전체를
 * 그대로 사용한다.
 */
import { loadIngredientResultFromApi } from '../api';

export type IngredientGrade = 'star' | 'good' | 'base';

export interface IngredientPurpose {
  name: string;
  description: string;
}

export interface IngredientRestriction {
  regulate_type: string;
  limit_cond: string;
}

export interface IngredientLlmSummary {
  summary_text: string;
  benefit_text: string;
  caution_text: string;
  usage_reason_text: string;
  caution_group_text: string;
  combo_recommendation: string;
}

/** 이 성분과 다른 성분 사이의 시너지/악화 조합 (DB ingredient_relation, LLM 아님). */
export interface IngredientRelationInfo {
  relation_type: string;
  user_message: string;
  related_ingredient_name: string;
}

export interface Ingredient {
  name_kr: string;
  name_en: string;
  display_grade: IngredientGrade;
  label_rank: number;
  safety_level: string;
  purposes: IngredientPurpose[];
  restricted: IngredientRestriction | null;
  relations: IngredientRelationInfo[];
  llm_summary: IngredientLlmSummary;
}

/** 카드 앞면 "핵심 성분" 그리드 한 칸 — DB의 슈퍼스타 성분만 대상. */
export interface KeyIngredient {
  name: string;
  /** 대표 배합목적 한 단어. 예: "주름개선". */
  purpose: string;
}

/** 카드 앞면 "사용 전 확인해 주세요" 한 항목 — DB의 배합 한도/금지/사용 제한 성분만 대상. */
export interface Caution {
  name: string;
  /** 주의가 필요한 이유 — DB의 restricted.limit_cond에 근거해야 하며 LLM이 임의로 새로 만들지 않는다. */
  reason: string;
}

export interface IngredientResultProduct {
  product_name: string;
  raw_ingredients: string;
  /**
   * 카드 앞면 최상단 — 전체 성분 구성을 함축한 자연스러운 문장 하나. "화면에서 가장 먼저,
   * 가장 크게" 읽히는 자리다. 성분명을 나열하지 않고(성분명 설명은 key_ingredients/
   * ingredient_explanation의 몫), 광고 카피처럼 과장하지 않고 DB에서 확인되는 배합목적
   * 범위 안에서만 표현한다. 아래 네 필드가 LLM 응답 전체를 이룬다
   * (docs/LLM_PROMPT.md의 출력 스키마와 동일).
   */
  summary: string;
  /** DB의 슈퍼스타 성분 → 그대로 매핑. 개수 제한 없음 — ResultSummaryPanel의 반응형 Grid가 그대로 받는다. */
  key_ingredients: KeyIngredient[];
  /** "성분 구성을 살펴보면" 본문 — 슈퍼스타+구디 성분을 근거로 상단 요약의 이유를 설명한다. */
  ingredient_explanation: string;
  /**
   * 스킨케어 루틴 안내 문구(LLM 아님, DB) — `app/product_category.py`가 제품 카테고리(스킨/토너,
   * 세럼/에센스/앰플, 크림 등)로부터 만든 고정 문구를 그대로 보여준다. 카테고리 미분류면
   * 빈 문자열(백엔드가 "" 그대로 내려줌) — 그 경우 섹션 자체를 숨긴다.
   */
  category_description: string;
  /**
   * 피부 타입별 위험/궁합 성분 요약 문장 — DB `ingredient_skin_score`를 집계한 것(LLM 아님,
   * `app/skin_fit.py summarize_skin_score_matches`). 매칭이 없으면 백엔드가 "..."를 내려주는데,
   * 그 경우 프론트가 빈 문자열로 취급해 섹션 자체를 숨긴다.
   */
  skin_score_summary: string;
  /** "사용 전 확인해 주세요" 목록 — 없으면 빈 배열(그러면 해당 섹션 자체가 렌더링되지 않는다). */
  cautions: Caution[];
}

export interface IngredientResult {
  product: IngredientResultProduct;
  ingredients: Ingredient[];
}

/**
 * 결과 화면 진입 요청 — 검색 리스트 클릭(search) / 스캔 OCR 성공(scan) 두 경로.
 * ResultView는 이 값을 받아 로딩 문구·에러 문구만 경로별로 갈라 보여주고,
 * 실제 데이터 형태(IngredientResult)는 두 경로가 동일하게 취급한다.
 */
export type IngredientResultRequest =
  | { source: 'search'; productId: string; productName: string }
  | { source: 'scan'; imageDataUrl: string };

/**
 * 결과 데이터 로더 — 검색/스캔 두 진입점을 하나의 함수로 받는다.
 * 실제 API 연동은 api.ts(loadIngredientResultFromApi) 참고 — search는 GET /products/{id},
 * scan(OCR)은 아직 백엔드에 연동 전이라 에러로 처리된다 (ResultView의 에러 화면으로 이어짐).
 */
export async function loadIngredientResult(request: IngredientResultRequest): Promise<IngredientResult> {
  return loadIngredientResultFromApi(request);
}
