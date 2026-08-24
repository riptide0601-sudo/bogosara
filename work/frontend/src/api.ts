/**
 * 백엔드(labellens FastAPI) 연동.
 *
 * 로컬 개발 기본값은 127.0.0.1:8000 — .env(VITE_API_BASE_URL)로 덮어쓸 수 있다.
 */
import type { Product } from './data/mockProducts';
import type { Ingredient, IngredientResult, IngredientResultRequest } from './data/ingredientResult';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

// ---- 백엔드 응답 원본 타입 (app/schemas/*.py 와 1:1) ----

interface ApiPurpose {
  purpose_id: number;
  purpose_name: string;
  description: string | null;
}

interface ApiLlmSummary {
  ingredient_id: number;
  summary_text: string | null;
  benefit_text: string | null;
  caution_text: string | null;
  usage_reason_text: string | null;
  caution_group_text: string | null;
  combo_recommendation: string | null;
}

interface ApiRelatedIngredient {
  ingredient_id: number;
  name_kr: string | null;
  name_en: string | null;
}

interface ApiIngredientRelation {
  relation_id: number;
  relation_type: string;
  user_message: string | null;
  related_ingredient: ApiRelatedIngredient;
}

interface ApiIngredient {
  ingredient_id: number;
  name_kr: string | null;
  name_en: string | null;
  safety_level: string | null;
  summary: string | null;
  purposes: ApiPurpose[];
  llm_summary: ApiLlmSummary | null;
}

interface ApiProductIngredient {
  label_rank: number | null;
  matched_text: string | null;
  ingredient: ApiIngredient;
  relations: ApiIngredientRelation[];
}

interface ApiProduct {
  product_id: string;
  product_name: string;
  brand: string | null;
  summary: string | null;
  composition_text: string | null;
  // app/core_ingredient_selector.py가 뽑아 DB엔 JSON 문자열로 저장되지만, 백엔드
  // ProductRead의 field_validator가 파싱해서 내려주므로 응답은 이미 배열이다.
  key_ingredients: string[];
  key_purposes: string[];
  // app/skin_fit.py summarize_skin_score_matches가 조립하는 문장. 매칭 없으면 백엔드가
  // "..."를 내려준다(모델 속성이 아니라 응답 시점에 계산되는 값이라 이게 "값 없음"의 표시).
  skin_score_summary: string;
  // app/product_category.py가 category로부터 만드는 고정 문구(computed_field). 카테고리
  // 미분류(OTHER)면 빈 문자열.
  category_description: string;
}

export interface ApiProductDetail extends ApiProduct {
  ingredients: ApiProductIngredient[];
  // label_rank 상위 DEFAULT_TOP_K개(핵심 성분 카드용) — product.key_ingredients(문자열
  // 배열)와 이름이 겹쳐서 백엔드가 top_ingredients로 따로 둔다 (app/schemas/product.py 참고).
  top_ingredients: ApiProductIngredient[];
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`API ${path} 실패: HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/** 검색 — GET /products?query=... 를 프론트 검색 카드(Product) 목록으로 변환. */
export async function searchProducts(query: string): Promise<Product[]> {
  const params = query ? `?query=${encodeURIComponent(query)}` : '';
  const products = await apiFetch<ApiProduct[]>(`/products${params}`);
  return products.map((p) => ({
    id: p.product_id,
    name: p.product_name,
    brand: p.brand ?? '',
    summary: p.summary ?? '',
  }));
}

/** core_ingredient_selector가 뽑은 핵심 성분 이름 집합. 없으면 빈 집합(전부 'good' 취급). */
function parseKeyIngredientNames(names: string[]): Set<string> {
  return new Set(names);
}

const GENERIC_PURPOSE_LABELS = new Set(['피부컨디셔닝제', '헤어컨디셔닝제', '네일컨디셔닝제']);
// 괄호 안 내용이 그 자체로 분류 태그일 뿐 라벨로는 무의미한 경우 — 앞의 본 이름을 대신 쓴다.
const NON_LABEL_PAREN_VALUES = new Set(['기타', '기능성화장품']);

/** "피부컨디셔닝제(보습제)" -> "보습제", "주름개선(기능성화장품)" -> "주름개선", "헤어컨디셔닝제" -> 그대로. */
function extractPurposeLabel(purposeName: string): string {
  const match = purposeName.match(/^(.*?)\(([^)]*)\)\s*$/);
  if (!match) return purposeName.trim();
  const [, base, paren] = match;
  return NON_LABEL_PAREN_VALUES.has(paren.trim()) ? base.trim() : paren.trim();
}

/**
 * 핵심 성분 카드 밑 짧은 라벨 — DB에 별도 "짧은 라벨" 컬럼은 없고, ingredient_purpose로 엮인
 * purpose.purpose_name에서 뽑는다. 여러 성분에 똑같이 반복되는 일반 분류명("피부컨디셔닝제" 등)
 * 말고 더 구체적인 라벨(예: "보습제", "주름개선")이 있으면 그걸 우선한다. DB에 아직 일반
 * 분류명만 걸려있는 성분은 그 이름 그대로 나온다 — LLM이 더 나은 한 단어를 골라줄 수 있는 지점.
 */
function pickShortPurposeLabel(purposes: ApiPurpose[]): string {
  if (purposes.length === 0) return '';
  const labels = purposes.map((p) => extractPurposeLabel(p.purpose_name));
  const specific = labels.find((label) => !GENERIC_PURPOSE_LABELS.has(label));
  return specific ?? labels[0];
}

function toIngredient(pi: ApiProductIngredient, starNames: Set<string>): Ingredient {
  const ing = pi.ingredient;
  const llm = ing.llm_summary;
  const shortPurposeLabel = pickShortPurposeLabel(ing.purposes);
  return {
    name_kr: ing.name_kr ?? '',
    name_en: ing.name_en ?? '',
    // display_grade는 백엔드에 없는 개념이라, product.key_ingredients(core_ingredient_selector가
    // 뽑은 이름 배열)에 있으면 'star', 없으면 'good'으로 로컬에서 임시 판정한다.
    display_grade: ing.name_kr && starNames.has(ing.name_kr) ? 'star' : 'good',
    label_rank: pi.label_rank ?? 0,
    safety_level: ing.safety_level ?? '일반',
    purposes: ing.purposes.map((p) => ({ name: p.purpose_name, description: p.description ?? '' })),
    // 배합 한도/금지 성분 데이터(규제)는 DB에 아직 없다 — safety_level도 현재 전부 비어있다.
    restricted: null,
    // 시너지/악화 조합 — DB ingredient_relation 그대로, LLM 아님.
    relations: pi.relations.map((r) => ({
      relation_type: r.relation_type,
      user_message: r.user_message ?? '',
      related_ingredient_name: r.related_ingredient.name_kr ?? '',
    })),
    llm_summary: {
      // summary_text만 DB 원문(ingredient.summary = 성분 정의)으로 폴백 가능. 나머지는 LLM 전용
      // 필드라 DB에 대응하는 원문이 없어서 빈 문자열로 둔다 — 컴포넌트가 값 없으면 그 섹션을
      // 안 그리므로(예: IngredientDetail의 benefit_text) 화면이 비어 보이는 대신 자연스럽게 숨는다.
      summary_text: llm?.summary_text || ing.summary || '', // Qwen 교체 지점
      benefit_text: llm?.benefit_text ?? '', // Qwen 교체 지점
      caution_text: llm?.caution_text ?? '', // Qwen 교체 지점 (DB 규제 있으면 그걸로도 채울 수 있음 — 현재 규제 데이터 없음)
      // 전성분 리스트 한 줄(IngredientRow)에 쓰이는 필드라, LLM 전에도 배합목적(DB)으로
      // "○○ 목적으로 배합." 정도는 채워둔다 — 완전히 빈 줄로 보이는 것보다 낫다.
      usage_reason_text: llm?.usage_reason_text || (shortPurposeLabel ? `${shortPurposeLabel} 목적으로 배합.` : ''), // Qwen 교체 지점
      caution_group_text: llm?.caution_group_text ?? '', // Qwen 교체 지점
      combo_recommendation: llm?.combo_recommendation ?? '', // Qwen 교체 지점
    },
  };
}

/**
 * ApiProductDetail(백엔드 응답, 또는 그와 동일한 모양의 정적 JSON) -> IngredientResult 변환.
 * 실시간 API 조회(fetchIngredientResult)와 모델 비교 화면(정적 eval/*.json 로딩) 둘 다 이 함수를
 * 공유한다 — 매핑 로직이 두 곳에서 갈라지지 않게.
 */
export function mapDetailToIngredientResult(detail: ApiProductDetail): IngredientResult {
  const starNames = parseKeyIngredientNames(detail.key_ingredients);

  return {
    product: {
      product_name: detail.product_name,
      raw_ingredients: detail.ingredients.map((pi) => pi.matched_text).filter(Boolean).join(', '),
      // 한 줄 요약(product.summary)과 성분 구성 줄글(product.composition_text)은 DB에서도 별도
      // 컬럼이다 — 합쳐서 하나로 쓰지 않는다.
      summary: detail.summary ?? '', // Qwen 교체 지점
      key_ingredients: detail.top_ingredients.map((pi) => ({
        name: pi.ingredient.name_kr ?? '',
        purpose: pickShortPurposeLabel(pi.ingredient.purposes),
      })),
      ingredient_explanation: detail.composition_text ?? '', // Qwen 교체 지점
      category_description: detail.category_description,
      // 매칭 없으면 백엔드가 "..."를 내려준다 — 그건 "값 없음"과 같은 뜻이라 빈 문자열로 취급.
      skin_score_summary: detail.skin_score_summary === '...' ? '' : detail.skin_score_summary,
      // 배합 한도/금지 성분 데이터는 아직 백엔드에 없다.
      cautions: [],
    },
    ingredients: detail.ingredients.map((pi) => toIngredient(pi, starNames)),
  };
}

/** 성분 결과 화면 — GET /products/{id} 를 IngredientResult로 변환. */
export async function fetchIngredientResult(productId: string): Promise<IngredientResult> {
  const detail = await apiFetch<ApiProductDetail>(`/products/${encodeURIComponent(productId)}`);
  return mapDetailToIngredientResult(detail);
}

/** App.tsx / ingredientResult.ts의 로더 시그니처에 맞춘 진입점. scan(OCR)은 아직 미연동. */
export async function loadIngredientResultFromApi(
  request: IngredientResultRequest,
): Promise<IngredientResult> {
  if (request.source === 'scan') {
    throw new Error('OCR 스캔 연동은 아직 준비되지 않았습니다.');
  }
  return fetchIngredientResult(request.productId);
}
