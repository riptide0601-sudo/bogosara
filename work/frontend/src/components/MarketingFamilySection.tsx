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
 */
export default function MarketingFamilySection({ families }: MarketingFamilySectionProps) {
  if (families.length === 0) return null;

  return (
    <div className="result-section">
      <h3 className="result-section-title">
        <span className="cursor">▶</span>상품명 성분, 진짜 들어있나요?
      </h3>
      <div className="family-block-list">
        {families.map((family) => {
          const exactCount = family.ingredients.filter((i) => i.match_type.startsWith('정확')).length;
          const relatedCount = family.ingredients.length - exactCount;
          const hasExact = exactCount > 0;

          return (
            <div className="family-block" key={family.name}>
              <div className="family-block-head">
                <span className="family-block-name">{family.name}</span>
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
