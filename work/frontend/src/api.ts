/**
 * 백엔드(labellens FastAPI) 연동.
 *
 * 로컬 개발 기본값은 127.0.0.1:8000 — .env(VITE_API_BASE_URL)로 덮어쓸 수 있다.
 */
import type { Product } from './data/mockProducts';
import type {
  Ingredient,
  IngredientResult,
  IngredientResultKeyIngredient,
  IngredientResultRequest,
  MatchedFamily,
  PurposeCount,
  SkinTypeCount,
} from './data/ingredientResult';

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
  // app/schemas/product.py의 computed_field — 올리브영에 등록된 상품별 직접 링크(goodsNo)는
  // DB에 없어서, 제품명으로 올리브영 검색 결과 페이지를 가리키는 URL을 그때그때 만들어 준다.
  oliveyoung_url: string;
  // app/static/images/products/{product_id}.* 를 가리키는 상대 경로(scripts/backfill_product_images.py로
  // 채움). 백엔드가 이 origin(API_BASE_URL)에서 정적 파일로 서빙하므로 프론트에서 절대 URL로
  // 붙여써야 한다(toAbsoluteImageUrl 참고) — Vite 개발 서버(5173) 기준 상대경로로 쓰면 404난다.
  image_url: string | null;
}

interface ApiProductSimilarity {
  product: ApiProduct;
  score: number;
}

interface ApiMatchedFamilyIngredient {
  ingredient_id: number;
  name_kr: string | null;
  label_rank: number | null;
  dosage: string | null;
  match_type: string;
  is_key_ingredient: boolean;
}

interface ApiMatchedFamily {
  family_id: number;
  name: string;
  from_product_name: boolean;
  matched_term: string | null;
  ingredients: ApiMatchedFamilyIngredient[];
}

export interface ApiProductDetail extends ApiProduct {
  ingredients: ApiProductIngredient[];
  // label_rank 상위 DEFAULT_TOP_K개(핵심 성분 카드용) — product.key_ingredients(문자열
  // 배열)와 이름이 겹쳐서 백엔드가 top_ingredients로 따로 둔다 (app/schemas/product.py 참고).
  top_ingredients: ApiProductIngredient[];
  // app/similarity.py의 코사인 유사도 기준 유사 제품(최대 10개, score 내림차순). 백엔드가
  // 이미 상세 조회에 같이 내려주므로 추천 제품에 별도 API 호출을 쓰지 않는다.
  similar_products: ApiProductSimilarity[];
  // app/marketing_families.py — 지정 상품 기준 마케팅 용어 ↔ 계열 묶음. 대상 밖 제품은 [].
  // optional인 이유: generate_compare.py가 만드는 정적 eval/*.json은 이 필드가 생기기 전
  // 스냅샷이라 아예 없을 수 있다 (toMatchedFamilies가 undefined를 []로 처리).
  ingredient_families?: ApiMatchedFamily[];
  // app/purpose_counts.py — 지정 상품 제한 없음. 위와 같은 이유로 optional.
  purpose_counts?: PurposeCount[];
  // app/skin_fit.py compute_skin_type_counts — 위와 같은 이유로 optional.
  skin_type_counts?: SkinTypeCount[];
}

/** image_url은 백엔드가 상대 경로로 내려주므로, 이미지를 실제로 서빙하는 백엔드 origin을 붙여야 한다
 * (프론트는 Vite 개발 서버(5173)에서 뜨고 API_BASE_URL(기본 8000)이 이미지도 같이 서빙함 — app/main.py 참고). */
function toAbsoluteImageUrl(imageUrl: string | null): string | null {
  return imageUrl ? `${API_BASE_URL}${imageUrl}` : null;
}

function toProduct(p: ApiProduct): Product {
  return {
    id: p.product_id,
    name: p.product_name,
    brand: p.brand ?? '',
    summary: p.summary ?? '',
    image_url: toAbsoluteImageUrl(p.image_url),
  };
}

// app/schemas/skin_fit.py의 SkinRiskRead와 1:1.
interface ApiSkinRiskIngredient {
  ingredient_id: number;
  name_kr: string | null;
  risk_type: string | null;
  reason: string | null;
  source: string | null;
}

export interface ApiSkinRisk {
  skin_type: string;
  has_risk: boolean;
  risk_ingredients: ApiSkinRiskIngredient[];
  total_ingredient_count: number;
}

/** GET /products/{id}/skin-fit — skin_type 생략 시 4개 피부 타입 전부 반환. 로그인한 유저의
 * skin_types와 대조해 개인화된 위험 성분을 보여주는 용도(ResultView.tsx 참고). */
export async function fetchSkinFit(productId: string): Promise<ApiSkinRisk[]> {
  return apiFetch<ApiSkinRisk[]>(`/products/${encodeURIComponent(productId)}/skin-fit`);
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
  return products.map(toProduct);
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
    ingredient_id: ing.ingredient_id,
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

function toMatchedFamilies(families: ApiMatchedFamily[] | undefined): MatchedFamily[] {
  // generate_compare.py가 만드는 정적 eval/*.json은 이 기능보다 먼저 만들어진 스냅샷이라
  // ingredient_families 필드 자체가 없을 수 있다 — 그때는 빈 배열(섹션 자체를 숨김)로 취급.
  if (!families) return [];
  return families.map((f) => ({
    name: f.name,
    from_product_name: f.from_product_name,
    matched_term: f.matched_term,
    ingredients: f.ingredients.map((i) => ({
      name_kr: i.name_kr ?? '',
      label_rank: i.label_rank,
      dosage: i.dosage,
      match_type: i.match_type,
      is_key_ingredient: i.is_key_ingredient,
    })),
  }));
}

/**
 * "핵심 성분" 카드용 — product.key_ingredients(core_ingredient_selector 큐레이션, 정제수/
 * 용제 등 제외)는 이름 문자열만 내려오므로, 이미 응답에 있는 전성분 전체(detail.ingredients)
 * 에서 같은 이름을 찾아 배합목적을 붙인다. top_ingredients(label_rank 상위 5개, 정제수가
 * 거의 항상 포함됨)를 쓰던 이전 방식과 달리 큐레이션된 이름·순서를 그대로 따른다.
 * 전성분 목록에서 이름이 안 찾아지는 경우(데이터 불일치)는 조용히 건너뛴다.
 */
function toKeyIngredients(detail: ApiProductDetail): IngredientResultKeyIngredient[] {
  const byName = new Map(detail.ingredients.map((pi) => [pi.ingredient.name_kr, pi]));
  return detail.key_ingredients.flatMap((name) => {
    const pi = byName.get(name);
    if (!pi) return [];
    return [{ name, purpose: pickShortPurposeLabel(pi.ingredient.purposes) }];
  });
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
      product_id: detail.product_id,
      product_name: detail.product_name,
      raw_ingredients: detail.ingredients.map((pi) => pi.matched_text).filter(Boolean).join(', '),
      // 한 줄 요약(product.summary)과 성분 구성 줄글(product.composition_text)은 DB에서도 별도
      // 컬럼이다 — 합쳐서 하나로 쓰지 않는다.
      summary: detail.summary ?? '', // Qwen 교체 지점
      key_ingredients: toKeyIngredients(detail),
      ingredient_explanation: detail.composition_text ?? '', // Qwen 교체 지점
      image_url: toAbsoluteImageUrl(detail.image_url),
      category_description: detail.category_description,
      oliveyoung_url: detail.oliveyoung_url,
      // 매칭 없으면 백엔드가 "..."를 내려준다 — 그건 "값 없음"과 같은 뜻이라 빈 문자열로 취급.
      skin_score_summary: detail.skin_score_summary === '...' ? '' : detail.skin_score_summary,
      skin_type_counts: detail.skin_type_counts ?? [],
      // 배합 한도/금지 성분 데이터는 아직 백엔드에 없다.
      cautions: [],
      ingredient_families: toMatchedFamilies(detail.ingredient_families),
      // {label, count, total} 모양이 백엔드 응답과 1:1이라 별도 변환 없이 그대로 씀 (없으면 []).
      purpose_counts: detail.purpose_counts ?? [],
      // similar_products는 이미 score 내림차순이므로 앞 3개가 곧 Top3.
      recommended_products: detail.similar_products.slice(0, 3).map((s) => toProduct(s.product)),
    },
    ingredients: detail.ingredients.map((pi) => toIngredient(pi, starNames)),
  };
}

// app/schemas/ingredient_family.py FamilyRankRead와 1:1.
export interface FamilyRankInfo {
  family_name: string;
  // 큐레이션은 돼있지만(product_family_member) 실제 전성분표에서 이 계열 성분을 하나도
  // 못 찾았을 때 false — 이땐 아래 필드가 전부 null/0이고, "없다"고 단정하는 대신
  // "{family_name} 성분 비교 데이터가 없어요"로 완곡하게 안내한다(ResultSummaryPanel 참고).
  has_data: boolean;
  representative_ingredient: string | null;
  // 라벨에 함량이 적혀있을 때만("2,400ppm", "0.2%" 등 원문 그대로) — 없으면 null.
  representative_concentration: string | null;
  label_rank: number | null;
  rank: number | null;
  total_count: number | null;
  average_label_rank: number | null;
  top_percentile: number | null;
  // 계열 내 큐레이션 제품들의 대표 성분 함량을 %로 환산한 평균 — 함량 표시된 제품이 하나도
  // 없으면 null.
  average_concentration_percent: number | null;
  // 위 평균이 몇 개 제품 값으로 계산됐는지(total_count 중 일부일 수 있음).
  concentration_sample_count: number;
}

/** GET /products/{id}/family-rank — "비슷한 제품과 비교하면" 카드(ResultSummaryPanel).
 * 한 제품이 여러 성분 계열에 동시에 큐레이션될 수 있어(예: 더마토리 히알샷 = 히알루론산 계열
 * + B5 계열) 배열로 온다. 어떤 계열에도 속하지 않으면 빈 배열(에러 아님) — 호출부가 섹션을 숨긴다. */
export async function fetchProductFamilyRank(productId: string): Promise<FamilyRankInfo[]> {
  const res = await fetch(`${API_BASE_URL}/products/${encodeURIComponent(productId)}/family-rank`);
  if (!res.ok) throw new Error(`family-rank 조회 실패: HTTP ${res.status}`);
  return res.json() as Promise<FamilyRankInfo[]>;
}

/** 성분 결과 화면 — GET /products/{id} 를 IngredientResult로 변환. */
export async function fetchIngredientResult(productId: string): Promise<IngredientResult> {
  const detail = await apiFetch<ApiProductDetail>(`/products/${encodeURIComponent(productId)}`);
  return mapDetailToIngredientResult(detail);
}

/** App.tsx / ingredientResult.ts의 로더 시그니처에 맞춘 진입점. scan(OCR)은 ScanOverlay가
 * 촬영 시점에 이미 /ocr/analyze를 호출해 결과를 들고 오므로, 여기서는 그 결과를 성분 요약
 * 카드 형태로 변환만 한다(mapOcrResultToIngredientResult). */
export async function loadIngredientResultFromApi(
  request: IngredientResultRequest,
): Promise<IngredientResult> {
  if (request.source === 'scan') {
    return mapOcrResultToIngredientResult(request.ocr);
  }
  return fetchIngredientResult(request.productId);
}

// ---- OCR 스캔 (app/routers/ocr.py POST /ocr/analyze) ----

/** app/schemas/ingredient.py IngredientDetail과 1:1 — ApiIngredient(검색 흐름)와 필드가
 * 같아 그 타입들(ApiPurpose/ApiLlmSummary)을 그대로 재사용한다. */
export interface OcrMatchedIngredient {
  ingredient_id: number;
  name_kr: string | null;
  name_en: string | null;
  safety_level: string | null;
  summary: string | null;
  purposes: ApiPurpose[];
  llm_summary: ApiLlmSummary | null;
}

export interface OcrIngredientMatch {
  label_rank: number;
  matched_text: string;
  /** 매칭된 표준 성분 상세 — DB에서 못 찾으면 null(전성분 리스트에서 그 토큰은 생략한다). */
  ingredient: OcrMatchedIngredient | null;
}

/** OCR이 사진에서 인식한 줄 하나 — 성분 요약 페이지가 사진 위에 형광펜으로 표시하는 데 쓴다
 * (app/schemas/ocr.py OcrTextRegion과 1:1). box_pct는 [x1,y1,x2,y2], 이미지 너비/높이 기준
 * 0~1 비율(픽셀 아님) — PhotoPanel이 표시 중인 사진 크기에 맞춰 변환한다. paddleocr 엔진일
 * 때만 채워지고, 다른 엔진이면 항상 빈 배열. */
export interface OcrTextRegion {
  text: string;
  box_pct: [number, number, number, number];
}

export interface OcrAnalyzeResult {
  engine: string;
  raw_ingredients: string[];
  results: OcrIngredientMatch[];
  text_regions: OcrTextRegion[];
}

/** 촬영한 프레임(canvas.toBlob 결과)을 업로드해 OCR + DB 성분 매칭을 실행한다
 * (ScanOverlay의 촬영 버튼 참고). raw_ingredients가 비어 있으면 "인식은 됐지만 아무 성분도
 * 못 읽었다"는 뜻이라, 호출부가 그 경우를 실패로 취급한다. */
export async function analyzeOcrImage(image: Blob, signal?: AbortSignal): Promise<OcrAnalyzeResult> {
  const form = new FormData();
  form.append('file', image, 'scan.png');
  const res = await fetch(`${API_BASE_URL}/ocr/analyze`, { method: 'POST', body: form, signal });
  if (!res.ok) {
    let detail = '';
    try {
      detail = ((await res.json()) as { detail?: string })?.detail ?? '';
    } catch {
      // 본문이 JSON이 아니면(예: 프록시 에러 페이지) 그냥 상태 코드만 쓴다.
    }
    throw new Error(detail || `OCR 분석 실패: HTTP ${res.status}`);
  }
  return res.json() as Promise<OcrAnalyzeResult>;
}

export interface ScanSummary {
  one_liner: string;
  composition_text: string;
}

/** 스캔 결과 화면의 한줄요약/성분구성 설명 — 검색 흐름(product.summary/composition_text)은
 * 미리 배치로 캐싱돼 있지만, 스캔은 등록된 Product가 없어 그 캐시가 없다. 그래서
 * ResultView가 결과 화면에 진입한 "다음" 이 함수를 비동기로 호출해 그 자리에서 LLM을
 * 돌린다(app/ocr_summary.py) — OCR 인식 자체(analyzeOcrImage)를 이것 때문에 더 기다리게
 * 하지 않으려고 별도 요청으로 분리했다. 근거(성분)가 너무 적으면 백엔드가 422를 주는데,
 * 그 경우 그냥 null을 반환해서 호출부가 기존 템플릿 문구를 그대로 쓰게 한다. */
export async function fetchScanSummary(rawIngredients: string[]): Promise<ScanSummary | null> {
  const res = await fetch(`${API_BASE_URL}/ocr/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_ingredients: rawIngredients }),
  });
  if (res.status === 422) return null;
  if (!res.ok) throw new Error(`스캔 요약 생성 실패: HTTP ${res.status}`);
  return res.json() as Promise<ScanSummary>;
}

/** OCR로 매칭된 성분 하나 -> 카드 뒷면 전성분 리스트용 Ingredient. toIngredient(검색 흐름)와
 * 거의 같은 매핑이지만, 스캔엔 제품별 큐레이션 데이터(relations, key_ingredients 기반
 * display_grade)가 없어 그 부분만 다르다. DB에 없는 토큰(ingredient===null)은 표준 성분명이
 * 아니라 카드로 만들 근거가 없어 호출부에서 건너뛴다. */
function ocrMatchToIngredient(match: OcrIngredientMatch): Ingredient | null {
  const ing = match.ingredient;
  if (!ing) return null;
  const llm = ing.llm_summary;
  const shortPurposeLabel = pickShortPurposeLabel(ing.purposes);
  return {
    ingredient_id: ing.ingredient_id,
    name_kr: ing.name_kr ?? '',
    name_en: ing.name_en ?? '',
    // 스캔은 core_ingredient_selector 큐레이션(핵심 성분 지정) 자체가 없어 항상 'good'.
    display_grade: 'good',
    label_rank: match.label_rank,
    safety_level: ing.safety_level ?? '일반',
    purposes: ing.purposes.map((p) => ({ name: p.purpose_name, description: p.description ?? '' })),
    restricted: null,
    // 시너지/악화 조합은 제품별 큐레이션이라 스캔엔 대응 데이터가 없다.
    relations: [],
    llm_summary: {
      summary_text: llm?.summary_text || ing.summary || '',
      benefit_text: llm?.benefit_text ?? '',
      caution_text: llm?.caution_text ?? '',
      usage_reason_text: llm?.usage_reason_text || (shortPurposeLabel ? `${shortPurposeLabel} 목적으로 배합.` : ''),
      caution_group_text: llm?.caution_group_text ?? '',
      combo_recommendation: llm?.combo_recommendation ?? '',
    },
  };
}

// app/purpose_counts.py의 _EXCLUDED_LABELS와 동일 — 순수 제형/기술 성분과 헤어/네일 전용
// 목적은 "이 성분들, 무슨 일을 하나요?" 요약에서 제외한다.
const PURPOSE_COUNT_EXCLUDED_LABELS = new Set([
  '용제', '유화제', '유화안정제', '수성', '비수성', '수렴제', 'pH 조정제',
  '금속이온봉쇄제', '피막형성제', '증량제', '결합제', '벌킹제', '불투명화제',
  '비계면활성', '비계면활성제', '흡수제', '변색방지제', '변성제', '안티케이킹제',
  '가소제', '감미제', '점도감소제',
  '헤어컨디셔닝제', '모발컨디셔닝제', '모발고정제',
]);

/** "이 성분들, 무슨 일을 하나요?" — app/purpose_counts.py compute_purpose_counts()의 스캔용
 * 라이브 집계판. 등록된 Product가 없어도 OCR로 매칭된 성분들의 purposes만으로 같은
 * 라벨링(extractPurposeLabel)·제외 규칙을 그대로 재구현할 수 있다 — 유일한 차이는
 * product.key_purposes 큐레이션이 없어 "우선순위 라벨" 정렬을 생략하고 개수 내림차순만
 * 쓴다는 것. */
function computeLivePurposeCounts(matches: OcrIngredientMatch[], limit = 6): PurposeCount[] {
  const total = matches.filter((m) => m.ingredient).length;
  if (total === 0) return [];

  const idsByLabel = new Map<string, Set<number>>();
  const descByLabel = new Map<string, string>();
  for (const match of matches) {
    if (!match.ingredient) continue;
    for (const p of match.ingredient.purposes) {
      const label = extractPurposeLabel(p.purpose_name);
      if (PURPOSE_COUNT_EXCLUDED_LABELS.has(label)) continue;
      if (!idsByLabel.has(label)) idsByLabel.set(label, new Set());
      idsByLabel.get(label)!.add(match.ingredient.ingredient_id);
      if (p.description && (!descByLabel.has(label) || p.purpose_name === label)) {
        descByLabel.set(label, p.description);
      }
    }
  }

  return [...idsByLabel.entries()]
    .sort((a, b) => b[1].size - a[1].size)
    .slice(0, limit)
    .map(([label, ids]) => ({
      label,
      count: ids.size,
      total,
      description: descByLabel.get(label) ?? null,
    }));
}

/**
 * OcrAnalyzeResult -> IngredientResult 변환. 스캔은 등록된 Product가 없어서 LLM이 미리
 * 만들어둔 한줄요약/핵심성분/성분설명, 그리고 제품명 기반 기능(계열 매칭·올리브영 링크·
 * 유사 제품 추천)은 대응할 데이터가 없다 — 전부 빈 값으로 두면 각 섹션이 기존의 "근거
 * 없으면 숨긴다" 규칙에 따라 자연스럽게 안 보인다. 반대로 카드 뒷면 전성분 리스트와
 * "이 성분들, 무슨 일을 하나요?"는 매칭된 성분들만으로 실제 값을 채울 수 있다.
 */
export function mapOcrResultToIngredientResult(ocr: OcrAnalyzeResult): IngredientResult {
  const ingredients = ocr.results
    .map(ocrMatchToIngredient)
    .filter((ing): ing is Ingredient => ing !== null);

  // ResultView.tsx가 결과 화면 진입 직후 fetchScanSummary()를 비동기로 호출해 이 문장을
  // 실제 LLM 한줄요약으로 갈아끼운다 — 그 전까지 잠깐 보이는 이 자리라 "확인했어요"(완료형)가
  // 아니라 "확인하고 있어요"(진행형)로 둬서, 별도 로딩 문구 없이 이 문장 자체가 "아직
  // 요약 중"이라는 걸 나타내게 한다.
  const summary =
    ingredients.length > 0
      ? `촬영한 전성분표에서 표준 성분 ${ingredients.length}종을 확인하고 있어요.`
      : '촬영한 전성분표에서 표준 성분을 찾지 못했어요.';

  return {
    product: {
      product_id: null,
      product_name: '스캔한 제품',
      raw_ingredients: ocr.raw_ingredients.join(', '),
      summary,
      key_ingredients: [],
      ingredient_explanation: '',
      image_url: null,
      category_description: '',
      oliveyoung_url: '',
      skin_score_summary: '',
      skin_type_counts: [],
      cautions: [],
      recommended_products: [],
      ingredient_families: [],
      purpose_counts: computeLivePurposeCounts(ocr.results),
    },
    ingredients,
  };
}
