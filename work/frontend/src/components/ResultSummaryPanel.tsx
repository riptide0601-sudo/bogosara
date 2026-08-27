import { useState, type ReactNode } from 'react';
import type { FamilyRankInfo } from '../api';
import type { IngredientResultProduct } from '../data/ingredientResult';
import type { FamilyRankState, SkinRiskInfo } from './ResultView';
import MarketingFamilySection from './MarketingFamilySection';
import PurposeCountSection from './PurposeCountSection';
import SkinTypeCountBars from './SkinTypeCountBars';

/** top_percentile(작을수록 좋음, 1~100)을 "상위권"류 4단계 문구로 변환. */
function percentileTierLabel(topPercentile: number): string {
  if (topPercentile <= 20) return '상위권';
  if (topPercentile <= 50) return '중상위권';
  if (topPercentile <= 80) return '중하위권';
  return '하위권';
}

/** "비슷한 제품과 비교하면" 카드 하나 — 여러 계열에 걸쳐 반복 렌더링된다(FamilyRankSection 참고).
 * has_data가 false면(큐레이션은 됐지만 전성분표에서 이 계열 성분을 못 찾은 경우) "없다"고
 * 단정하지 않고 "비교 데이터가 없다"로 완곡하게 안내만 한다. */
function FamilyRankCard({ item }: { item: FamilyRankInfo }) {
  if (!item.has_data) {
    return (
      <div className="result-family-rank">
        <p className="result-family-rank-family">{item.family_name}</p>
        <p className="result-family-rank-no-data">{item.family_name} 성분 비교 데이터가 없어요</p>
      </div>
    );
  }

  return (
    <div className="result-family-rank">
      <p className="result-family-rank-family">{item.family_name}</p>
      <p className="result-family-rank-ingredient">
        대표 성분 · {item.representative_ingredient}
        {item.representative_concentration && (
          <span className="result-family-rank-pct"> ({item.representative_concentration})</span>
        )}
      </p>
      <p className="result-family-rank-rank">
        {item.rank}위 / {item.total_count}개 중
      </p>
      <p className="result-family-rank-detail">
        이 제품은 함량 순위 {percentileTierLabel(item.top_percentile!)}이에요
        <span className="result-family-rank-avg">평균: 전성분 {item.average_label_rank}번째</span>
      </p>
      {item.average_concentration_percent != null && (
        <div className="result-family-rank-conc">
          <span className="result-family-rank-conc-label">계열 평균 함량</span>
          <span className="result-family-rank-conc-value">{item.average_concentration_percent}%</span>
          <span className="result-family-rank-conc-note">
            함량 표시된 {item.concentration_sample_count}개 제품 기준
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * "비슷한 제품과 비교하면" 섹션 전체 — 한 제품이 여러 계열에 동시에 속할 수 있어(예: 더마토리
 * 히알샷 = 히알루론산 계열 + B5 계열) top_percentile이 가장 좋은(작은) 계열 하나만 기본으로
 * 펼쳐 보여주고, 나머지 계열은 "{family_name} 보기" 토글 버튼 뒤에 접어둔다. 계열이 하나뿐이면
 * 토글 없이 그 하나만 보인다.
 */
function FamilyRankSection({ items }: { items: FamilyRankInfo[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // has_data가 false인 항목(순위 정보 없음)은 항상 맨 뒤로 — 대표로 뽑힐 실제 순위가
  // 하나라도 있으면 그게 우선이다.
  const sorted = [...items].sort((a, b) => {
    if (a.has_data !== b.has_data) return a.has_data ? -1 : 1;
    if (!a.has_data) return 0;
    return a.top_percentile! - b.top_percentile!;
  });
  const [primary, ...rest] = sorted;

  const toggle = (familyName: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(familyName)) next.delete(familyName);
      else next.add(familyName);
      return next;
    });
  };

  return (
    <div className="result-family-rank-list">
      <FamilyRankCard item={primary} />
      {rest.map((item) => (
        <div key={item.family_name}>
          <button
            type="button"
            className="result-family-rank-toggle"
            aria-expanded={expanded.has(item.family_name)}
            onClick={(e) => {
              // 카드 앞면 전체가 클릭 시 뒤집히는 버튼이라(ResultCard의 flipToBack), 이 버튼
              // 클릭이 거기로 버블링되면 토글과 동시에 카드가 뒤집혀 버린다 — 막아야 한다.
              e.stopPropagation();
              toggle(item.family_name);
            }}
          >
            <span className="cursor">▶</span>
            {item.family_name} {expanded.has(item.family_name) ? '접기' : '보기'}
          </button>
          {expanded.has(item.family_name) && <FamilyRankCard item={item} />}
        </div>
      ))}
    </div>
  );
}

/** 한 줄 요약 문장이 보통 "{제품명}은/는 ..."으로 시작하는데, 제품명은 바로 위 헤더 줄에서
 * 이미 보여주므로 이 문장에서는 그 앞머리만 잘라내고 설명부터 보여준다. */
function stripProductNameLead(summary: string, productName: string): string {
  if (!productName || !summary.startsWith(productName)) return summary;
  return summary.slice(productName.length).replace(/^(은|는|이|가)?\s*/, '');
}

/** "성분 구성을 살펴보면"(composition_text)의 `**볼드**` 마크다운을 <strong>으로 렌더링한다.
 * prompts/product_summary.md 지시대로 핵심 성분명·스킨케어 순서 문구만 감싸져 있다고 가정 —
 * 그 외 마크다운(제목/목록 등)은 안 쓰기로 했으니 굳이 마크다운 라이브러리를 안 붙였다. */
function renderBoldText(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    const m = part.match(/^\*\*([^*]+)\*\*$/);
    return m ? <strong key={i}>{m[1]}</strong> : part;
  });
}

interface ResultSummaryPanelProps {
  product: IngredientResultProduct;
  /** 우측 상단 "카드를 눌러 전성분 N개 보기" 표기에 쓰는 전체 성분 개수 (카드 뒷면과 동일한 ingredients.length). */
  totalCount: number;
  isScan: boolean;
  /** 로그인한 유저의 마이페이지 피부 타입 기준 개인화된 위험 성분 (ResultView.tsx가 조회). */
  skinRisk: SkinRiskInfo;
  /** "비슷한 제품과 비교하면" — 성분 계열 순위 (ResultView.tsx가 조회). */
  familyRank: FamilyRankState;
  /** 카드가 뒷면으로 넘어가 있는지 — "카드를 눌러 전성분 N개 보기" 버튼의 aria-expanded에 쓴다. */
  isFlipped: boolean;
  /** "카드를 눌러 전성분 N개 보기" 클릭 시 카드 뒤집기 (ResultCard의 flipToBack). */
  onFlip: () => void;
  /** 핵심 성분 칩 클릭 시 그 성분 이름으로 상세 뷰를 연다 (ResultCard의 handleSelectFromChip). */
  onSelectIngredient: (name: string) => void;
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
 *   풀어서 설명한다 — 상단 요약 문장을 그대로 반복하지 않는다. 스킨케어 순서(옛
 *   category_description 전용 섹션)도 이제 이 문단 안에 자연스럽게 녹여져 있다
 *   (prompts/product_summary.md 참고) — 별도 섹션으로 안 뺀다. 핵심 성분명·스킨케어
 *   순서 문구는 `**볼드**`로 와서 renderBoldText가 <strong>으로 렌더링한다.
 * - 피부 타입별 참고(skin_type_counts): DB ingredient_skin_score를 집계한 피부타입별
 *   좋음/유의 성분 개수(app/skin_fit.py compute_skin_type_counts, LLM 아님) — 줄글이 아니라
 *   막대바로 보여준다(SkinTypeCountBars). 매칭 없으면 빈 배열 — 섹션 자체를 숨긴다.
 * - 주의사항(cautions): DB의 배합 한도/금지/사용 제한 성분이 있을 때만 렌더링한다. 성분명이
 *   먼저, 이유가 그 아래에 오도록 위계를 둔다.
 *
 * "카드를 눌러 전성분 N개 보기" 힌트는 카드 맨 아래(예전엔 여기 구분선 + 여백까지 차지했다)
 * 대신 제품명과 같은 줄, 우측 상단에 붙인다 — 스크롤을 줄이려는 목적. 카드 앞면 전체가 아니라
 * 이 버튼 자체가 클릭 영역이다(ResultCard의 flipToBack을 onFlip으로 받아 호출).
 */
export default function ResultSummaryPanel({
  product,
  totalCount,
  isScan,
  skinRisk,
  familyRank,
  isFlipped,
  onFlip,
  onSelectIngredient,
}: ResultSummaryPanelProps) {
  const {
    summary,
    key_ingredients,
    ingredient_explanation,
    skin_type_counts,
    cautions,
    oliveyoung_url,
    ingredient_families,
    purpose_counts,
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

      {/* 1-1. 상품명 성분, 진짜 들어있나요? — 마케팅 용어 ↔ 계열 묶음 (지정 상품만, 근거 없으면 숨김) */}
      <MarketingFamilySection families={ingredient_families} />

      {/* 2. 핵심 성분 */}
      {key_ingredients.length > 0 && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>핵심 성분
          </h3>
          <ul className={`result-ing-chips ${chipsSizeClass}`}>
            {key_ingredients.map((item) => (
              <li key={item.name} className="result-ing-chip">
                <button
                  type="button"
                  className="result-ing-chip-btn"
                  onClick={() => onSelectIngredient(item.name)}
                >
                  <span className="result-ing-chip-name">{item.name}</span>
                  <span className="result-ing-chip-purpose">{item.purpose}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 2-1. 이 성분들, 무슨 일을 하나요? — 배합목적 카운트 (근거 없으면(배합목적 데이터 자체가 없으면) 숨김) */}
      <PurposeCountSection purposeCounts={purpose_counts} />

      {/* 3. 성분 구성을 살펴보면 — 스킨케어 순서(옛 4번 섹션)도 이 문단 안에 녹여져 있다
          (prompts/product_summary.md 참고). 핵심 성분명·스킨케어 순서 문구는 **볼드**로
          와서 renderBoldText가 <strong>으로 렌더링한다. */}
      {ingredient_explanation && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>성분 구성을 살펴보면
          </h3>
          <p className="result-explain">{renderBoldText(ingredient_explanation)}</p>
        </div>
      )}

      {/* 3-1. 비슷한 제품과 비교하면 — GET /products/{id}/family-rank(ResultView.tsx가 조회).
          이 제품이 어떤 성분 계열(scripts/backfill_ingredient_families.py)에도 속하지
          않으면(status: 'none') 섹션 자체를 숨긴다 — 에러가 아니라 정상 상태. 한 제품이 여러
          계열에 동시에 속할 수 있어(예: 히알루론산+B5) 계열마다 카드를 하나씩 반복한다. */}
      {familyRank.status === 'ok' && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>비슷한 제품과 비교하면
          </h3>
          <FamilyRankSection items={familyRank.data} />
        </div>
      )}

      {/* 5. 피부 타입별 참고 — DB ingredient_skin_score 집계(LLM 아님), 매칭 있을 때만.
          줄글 대신 피부타입별 좋음/유의 막대바로 보여준다 (SkinTypeCountBars 참고). */}
      {skin_type_counts.length > 0 && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>피부 타입별 참고
          </h3>
          <SkinTypeCountBars skinTypeCounts={skin_type_counts} />
        </div>
      )}

      {/* 5-1. 내 피부 타입 기준 — 마이페이지에 등록한 피부 타입(로그인 필요)과 대조한
          개인화된 위험 성분(app/skin_fit.py GET /products/{id}/skin-fit). 위의 "피부 타입별
          참고"는 전체 4개 타입을 요약한 일반 문구고, 이건 로그인한 유저 본인 기준만 본다. */}
      {skinRisk.status !== 'error' && (
        <div className="result-section">
          <h3 className="result-section-title">
            <span className="cursor">▶</span>내 피부 타입 기준
          </h3>
          {skinRisk.status === 'signed-out' && (
            <p className="result-explain">로그인하면 내 피부 타입 기준 위험 성분을 알려드려요.</p>
          )}
          {skinRisk.status === 'no-skin-type' && (
            <p className="result-explain">마이페이지에서 피부 타입을 등록하면 여기에 표시돼요.</p>
          )}
          {skinRisk.status === 'loading' && <p className="results-status">불러오는 중...</p>}
          {skinRisk.status === 'ok' && skinRisk.risks.length === 0 && (
            <p className="result-explain">등록하신 피부 타입 기준으로 주의할 성분이 없어요.</p>
          )}
          {skinRisk.status === 'ok' && skinRisk.risks.length > 0 && (
            <ul className="result-caution-list">
              {skinRisk.risks.map((risk) => (
                <li key={risk.skinType} className="result-caution-item">
                  <p className="result-caution-name">{risk.skinType}</p>
                  {risk.ingredients.map((ing) => (
                    <p key={ing.name} className="result-caution-reason">
                      {ing.name} — {ing.reason}
                    </p>
                  ))}
                </li>
              ))}
            </ul>
          )}
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
