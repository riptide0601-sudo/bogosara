import { useState } from 'react';
import type { MatchedFamily } from '../data/ingredientResult';

interface MarketingFamilySectionProps {
  families: MatchedFamily[];
}

/**
 * "상품명 성분, 진짜 들어있나요?" — 상품명에 나오는 마케팅 용어(히알루론산/콜라겐/PDRN 등)가
 * 실제 전성분에 얼마나 들어있는지 계열별로 묶어 보여준다 (app/marketing_families.py 참고).
 * 최대 3계열, 상품명에 등장한 용어 우선 → 그 외 실제 매칭되는 계열 순.
 *
 * 계열 안에서도 "정확(어근일치/DB 정의문 근거)"와 "유연물질(관련이지만 다른 물질)"을 배지·칩
 * 색으로 구분한다 — 예: "메디힐 콜라겐 탄력 세럼"엔 콜라겐 자체가 아니라 콜라겐 합성을
 * 촉진한다는 펩타이드만 들어있는데, 이걸 그냥 "1종 확인"으로 뭉뚱그리면 정작 이 기능이
 * 잡아내야 할 "이름과 실제 성분이 다른" 케이스를 숨기게 된다. 그래서 정확 매칭이 0건이면
 * 배지 자체를 "직접 함유 없음 · 관련 성분 M종"으로 다르게 보여준다.
 *
 * 계열 성분이면서 동시에 이 제품의 핵심 성분(product.key_ingredients)이기도 하면
 * `is_key_ingredient`가 true — 별표(★) + 칩 전체를 accent-dark로 꽉 채워서(family-chip--key)
 * "핵심 성분 카드"와 같은 톤으로 눈에 띄게 한다. 정확/유연물질 구분보다 우선순위가 높은
 * 시각 신호라 두 스타일이 겹치면 --key가 이긴다(CSS 참고).
 *
 * from_product_name(상품명 유래 계열)이면 계열 이름을 <mark>(.term-highlight)로 형광펜
 * 표시한다 — ResultSummaryPanel이 상품명 헤더에서 같은 스타일로 matched_term을 표시해서,
 * "상품명의 이 단어 -> 이 계열"이 시각적으로 이어져 보이게 한다.
 *
 * 레이아웃(리디자인, 2026-08-28): family-block-list는 2열 그리드다. 성분이 3종 이상인
 * 계열은 칩이 한 줄을 넘기기 쉬워서 grid-column을 두 칸 다 차지하게(family-block--full)
 * 하고, 1~2종인 계열은 한 칸만 차지해서 두 개가 나란히 붙어 빈 공간이 안 남게 한다.
 *
 * 범례 아코디언(2026-08-28): 색·별표·"N번째"가 뭘 뜻하는지는 매번 안 봐도 되는 부가
 * 설명이라, "성분 카드 색 차이는 무엇인가요?"를 누르면 펼쳐지는 아코디언으로 접어뒀다 —
 * 기본은 접힘. 계열 박스 자체는 아코디언과 무관하게 항상 보인다.
 */
export default function MarketingFamilySection({ families }: MarketingFamilySectionProps) {
  const [legendOpen, setLegendOpen] = useState(false);

  if (families.length === 0) return null;

  return (
    <div className="result-section">
      <h3 className="result-section-title">
        <span className="cursor">▶</span>상품명 성분, 진짜 들어있나요?
      </h3>
      <p className="result-section-desc">
        상품명에 등장하는 성분 이름이 실제 전성분에도 들어있는지 계열별로 확인해요.
      </p>
      <p className="family-legend-title">
        <button
          type="button"
          className="family-legend-toggle"
          aria-expanded={legendOpen}
          onClick={(e) => {
            // 이 섹션이 결과 카드(ResultCard) 앞면 안에 있고, 그 앞면 자체가 클릭하면
            // 전성분 뒷면으로 뒤집히는 큰 클릭 영역이라, 없으면 카드가 같이 뒤집혀 버린다.
            e.stopPropagation();
            setLegendOpen((v) => !v);
          }}
        >
          성분 카드 색 차이는 무엇인가요?
          <span className="purpose-count-chevron" aria-hidden="true">
            {legendOpen ? '▾' : '▸'}
          </span>
        </button>
      </p>
      {legendOpen && (
        <p className="family-legend">
          <span className="family-legend-item">
            <span className="family-legend-swatch family-legend-swatch--exact" />
            이 성분 계열에 정확히 일치
          </span>
          <span className="family-legend-item">
            <span className="family-legend-swatch family-legend-swatch--related" />
            관련 있지만 다른 물질
          </span>
          <span className="family-legend-item">
            <span className="family-legend-swatch family-legend-swatch--key" />
            핵심 성분
          </span>
          <span className="family-legend-item">
            <span className="family-chip-star">★</span>
            핵심 성분
          </span>
          {/* "N번째"(label_rank)가 뭘 뜻하는지 — 전성분 표시 규정상 배합량이 많은 순으로
              적으므로, 숫자가 작을수록(앞쪽일수록) 그 성분이 많이 들어있다는 뜻. 위 색·별표
              범례와 같은 한 줄에 이어서 보여준다(별도 줄로 빼면 두 줄이 된다). */}
          <span className="family-legend-item family-legend-item--note">
            · "N번째"는 전성분표 순서(앞쪽일수록 함유량 많음)
          </span>
        </p>
      )}
      <div className="family-block-list">
        {families.map((family) => {
          const exactCount = family.ingredients.filter((i) => i.match_type.startsWith('정확')).length;
          const relatedCount = family.ingredients.length - exactCount;
          const hasExact = exactCount > 0;

          const blockClass = `family-block${family.ingredients.length >= 3 ? ' family-block--full' : ''}`;

          return (
            <div
              className={blockClass}
              key={family.name}
              // 상품명 헤더의 형광펜 용어를 누르면 이 계열 박스로 점선 화살표가 이어지는
              // 애니메이션을 그린다(ResultSummaryPanel의 handleTermClick 참고) — 그 클릭
              // 핸들러가 이 값으로 목표 박스를 찾는다.
              data-matched-term={family.from_product_name && family.matched_term ? family.matched_term : undefined}
            >
              <div className="family-block-head">
                <span className="family-block-name">
                  {family.from_product_name && family.matched_term ? (
                    <mark className="term-highlight">{family.name}</mark>
                  ) : (
                    family.name
                  )}
                </span>
                <span className={`family-badge ${hasExact ? 'family-badge--ok' : 'family-badge--none'}`}>
                  {hasExact ? `${exactCount}종 확인` : `직접 함유 없음 · 관련 성분 ${relatedCount}종`}
                </span>
              </div>
              <ul className="family-chip-row">
                {family.ingredients.map((ing) => {
                  const isExact = ing.match_type.startsWith('정확');
                  const metaParts = [
                    ing.label_rank != null ? `${ing.label_rank}번째` : null,
                    ing.dosage,
                    isExact ? null : '관련 성분',
                  ].filter(Boolean);
                  const chipClass = [
                    'family-chip',
                    isExact ? 'family-chip--exact' : 'family-chip--related',
                    ing.is_key_ingredient && 'family-chip--key',
                  ]
                    .filter(Boolean)
                    .join(' ');
                  return (
                    <li
                      key={ing.name_kr}
                      className={chipClass}
                      title={ing.is_key_ingredient ? '이 제품의 핵심 성분이기도 해요' : undefined}
                    >
                      <span className="family-chip-name">
                        {ing.is_key_ingredient && <span className="family-chip-star">★</span>}
                        {ing.name_kr}
                      </span>
                      {metaParts.length > 0 && <span className="family-chip-meta">{metaParts.join(' · ')}</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
