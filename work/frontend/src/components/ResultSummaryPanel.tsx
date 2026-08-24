import type { IngredientResultProduct } from '../data/ingredientResult';

/** 한 줄 요약 문장이 보통 "{제품명}은/는 ..."으로 시작하는데, 제품명은 바로 위 헤더 줄에서
 * 이미 보여주므로 이 문장에서는 그 앞머리만 잘라내고 설명부터 보여준다. */
function stripProductNameLead(summary: string, productName: string): string {
  if (!productName || !summary.startsWith(productName)) return summary;
  return summary.slice(productName.length).replace(/^(은|는|이|가)?\s*/, '');
}

interface ResultSummaryPanelProps {
  product: IngredientResultProduct;
  /** 우측 상단 "카드를 눌러 전성분 N개 보기" 표기에 쓰는 전체 성분 개수 (카드 뒷면과 동일한 ingredients.length). */
  totalCount: number;
  isScan: boolean;
  /** 카드가 뒷면으로 넘어가 있는지 — "카드를 눌러 전성분 N개 보기" 버튼의 aria-expanded에 쓴다. */
  isFlipped: boolean;
  /** "카드를 눌러 전성분 N개 보기" 클릭 시 카드 뒤집기 (ResultCard의 flipToBack). */
  onFlip: () => void;
}

/**
 * 결과 화면 상단(카드 앞면) — 위에서 아래로 다음 순서로 읽히게 배치한다:
 *   한 문장 요약 → 핵심 성분 → 성분 구성 설명 → 스킨케어 순서 → 피부 타입별 참고 → 주의사항
 *
 * 여섯 블록 모두 `product`에서 그대로 옮겨온다 — 개별 필드가 어떤 DB 등급/LLM 여부에서
 * 왔는지는 `data/ingredientResult.ts`의 IngredientResultProduct 주석과 docs/API.md 참고.
 * "슈퍼스타"/"구디" 같은 내부 등급 명칭은 이 화면(카드 앞면)에도, 카드 뒷면에도 노출하지
 * 않는다 — 카드 뒷면 배지(IngredientRow/IngredientDetail의 getIngredientBadge)도 사용자
 * 용어(핵심성분/일반성분/유의성분)로만 보여준다. 아이콘/이모티콘은 새로 추가하지 않는다 —
 * 위계는 폰트 크기·굵기·여백·구분선 강약만으로 표현한다.
 *
 * - 한 문장 요약(summary): 전체 성분 구성을 함축한 문장 하나만 보여준다 — 성분명을 나열하지
 *   않고, 짧은 설명/태그로 쪼개지도 않는다(그 역할은 핵심 성분·성분 구성 설명이 나눠 맡는다).
 *   이 카드에서 가장 먼저·가장 크게 읽혀야 하는 자리라 제일 크게 키운다.
 * - 핵심 성분(key_ingredients): DB 슈퍼스타 성분 → 이름 + 대표 배합목적만, 개수 제한 없이
 *   기존 반응형 Grid(.result-ing-chips, 개수별 크기 조절 포함)를 그대로 재사용한다. 칸 안에서도
 *   성분명이 대표 배합목적보다 눈에 띄게 크고 굵어야 한다(위계는 CSS 참고).
 * - 성분 구성 설명(ingredient_explanation): 슈퍼스타+구디 성분을 근거로 상단 요약의 이유를
 *   풀어서 설명한다 — 상단 요약 문장을 그대로 반복하지 않는다.
 * - 스킨케어 순서(category_description): DB(app/product_category.py)가 카테고리로부터 만든
 *   고정 문구를 그대로 보여준다(LLM 아님). 카테고리 미분류면 빈 문자열 — 섹션 자체를 숨긴다.
 * - 피부 타입별 참고(skin_score_summary): DB ingredient_skin_score를 집계한 문장 하나
 *   (app/skin_fit.py summarize_skin_score_matches, LLM 아님). 매칭 없으면(백엔드가 "..."로
 *   내려주면) 섹션 자체를 숨긴다.
 * - 주의사항(cautions): DB의 배합 한도/금지/사용 제한 성분이 있을 때만 렌더링한다. 성분명이
 *   먼저, 이유가 그 아래에 오도록 위계를 둔다.
 *
 * "카드를 눌러 전성분 N개 보기" 힌트는 카드 맨 아래(예전엔 여기 구분선 + 여백까지 차지했다)
 * 대신 제품명과 같은 줄, 우측 상단에 붙인다 — 스크롤을 줄이려는 목적. 카드 앞면 전체가 아니라
 * 이 버튼 자체가 클릭 영역이다(ResultCard의 flipToBack을 onFlip으로 받아 호출).
 */
export default function ResultSummaryPanel({ product, totalCount, isScan, isFlipped, onFlip }: ResultSummaryPanelProps) {
  const {
    summary,
    key_ingredients,
    ingredient_explanation,
    category_description,
    skin_score_summary,
    cautions,
    oliveyoung_url,
  } = product;
  const displayName = isScan ? '스캔한 제품' : product.product_name;
  const headline = stripProductNameLead(summary, product.product_name);

  const chipsSizeClass =
    key_ingredients.length === 1
      ? 'result-ing-chips--single'
      : key_ingredients.length <= 3
        ? 'result-ing-chips--few'
        : 'result-ing-chips--many';

  return (
    <section className="result-summary" aria-labelledby="result-summary-title">
      <div className="result-summary-header">
        <p className="result-product-name" id="result-summary-title">
          📄 {displayName}
        </p>
        <button type="button" className="result-flip-hint" aria-expanded={isFlipped} onClick={onFlip}>
          <span className="cursor">▶</span>카드를 눌러 전성분 {totalCount}개 보기
        </button>
      </div>

      {/* 1. 한 문장 요약 — 이 카드에서 가장 먼저, 가장 크게 읽혀야 하는 자리.
          따옴표로 감싸서 "LLM이 이 제품을 한 문장으로 인용해준다"는 느낌을 준다. */}
      <p className="result-headline">“{headline}”</p>

      {/* 올리브영 검색 결과 페이지 링크 — 상품별 직접 링크(goodsNo)는 DB에 없어서
          백엔드가 제품명으로 만든 검색 페이지 URL이다(app/schemas/product.py computed_field). */}
      <a
        className="result-oliveyoung-link"
        href={oliveyoung_url}
        target="_blank"
        rel="noopener noreferrer"
      >
        <span className="cursor">▶</span>올리브영에서 찾아보기 ↗
      </a>

      {/* 2. 핵심 성분 */}
      {key_ingredients.length > 0 && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>핵심 성분
          </h3>
          <ul className={`result-ing-chips ${chipsSizeClass}`}>
            {key_ingredients.map((item) => (
              <li key={item.name} className="result-ing-chip">
                <span className="result-ing-chip-name">{item.name}</span>
                <span className="result-ing-chip-purpose">{item.purpose}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 3. 성분 구성을 살펴보면 */}
      {ingredient_explanation && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>성분 구성을 살펴보면
          </h3>
          <p className="result-explain">{ingredient_explanation}</p>
        </div>
      )}

      {/* 4. 스킨케어 순서 — DB product_category 고정 문구(LLM 아님), 카테고리 분류됐을 때만 */}
      {category_description && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>스킨케어 순서
          </h3>
          <p className="result-explain">{category_description}</p>
        </div>
      )}

      {/* 5. 피부 타입별 참고 — DB ingredient_skin_score 집계(LLM 아님), 매칭 있을 때만 */}
      {skin_score_summary && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>피부 타입별 참고
          </h3>
          <p className="result-explain">{skin_score_summary}</p>
        </div>
      )}

      {/* 6. 사용 전 확인해 주세요 — 주의사항이 있을 때만 */}
      {cautions.length > 0 && (
        <div className="result-section result-section--caution">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>사용 전 확인해 주세요
          </h3>
          <ul className="result-caution-list">
            {cautions.map((caution) => (
              <li key={caution.name} className="result-caution-item">
                <p className="result-caution-name">{caution.name}</p>
                <p className="result-caution-reason">{caution.reason}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
