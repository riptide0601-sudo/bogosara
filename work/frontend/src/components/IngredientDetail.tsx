import { useEffect, useRef } from 'react';
import type { Ingredient } from '../data/ingredientResult';
import { getIngredientBadge } from '../data/ingredientGrade';

interface IngredientDetailProps {
  ingredient: Ingredient;
  onBack: () => void;
}

/**
 * 전성분 리스트에서 성분 하나를 클릭했을 때, 카드 뒷면 전체를 차지하며 뜨는 상세 뷰.
 * 상세설명(summary_text) → 좋은 점(benefit_text) → 나쁜 점(caution_text) → 배합목적 →
 * 궁합 팁(combo_recommendation) 순으로 보여준다. 색은 새로 만들지 않고 대신
 * "실선+accent-soft(좋은 점)" ↔ "실선+sub(나쁜 점)" ↔ "점선(그 외 정보)" 보더 스타일로 구분한다.
 */
export default function IngredientDetail({ ingredient, onBack }: IngredientDetailProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const badge = getIngredientBadge(ingredient);
  const { summary_text, benefit_text, caution_text, combo_recommendation } = ingredient.llm_summary;

  // 성분이 바뀔 때마다(다른 성분 클릭 시에도) 상세 뷰 제목으로 포커스를 옮겨 스크린리더가 새 내용을 읽게 한다.
  useEffect(() => {
    headingRef.current?.focus();
  }, [ingredient]);

  return (
    <div className="ing-detail" role="region" aria-label={`${ingredient.name_kr} 상세 정보`}>
      <button type="button" className="flip-back-btn" onClick={onBack}>
        <span className="cursor">◀</span>목록으로
      </button>

      <div className="ing-detail-head">
        <span className={`ing-badge ${badge.className}`}>{badge.label}</span>
        <div>
          <h3 className="ing-detail-name" ref={headingRef} tabIndex={-1}>
            {ingredient.name_kr} <span className="ing-name-en">{ingredient.name_en}</span>
          </h3>
          <p className="ing-detail-safety">안전 등급 · {ingredient.safety_level}</p>
        </div>
      </div>

      {ingredient.restricted && (
        <p className="ing-pill ing-pill--block">
          ⚠ {ingredient.restricted.regulate_type} — {ingredient.restricted.limit_cond}
        </p>
      )}

      {summary_text && (
        <section className="ing-detail-section">
          <h4 className="ing-detail-title">
            <span className="cursor">▶</span>상세설명
          </h4>
          <p>{summary_text}</p>
        </section>
      )}

      {benefit_text && (
        <section className="ing-detail-section ing-detail-section--good">
          <h4 className="ing-detail-title">
            <span className="cursor">▶</span>좋은 점
          </h4>
          <p>{benefit_text}</p>
        </section>
      )}

      {caution_text && (
        <section className="ing-detail-section ing-detail-section--caution">
          <h4 className="ing-detail-title">
            <span className="cursor">▶</span>나쁜 점
          </h4>
          <p>{caution_text}</p>
        </section>
      )}

      {ingredient.purposes.length > 0 && (
        <section className="ing-detail-section">
          <h4 className="ing-detail-title">
            <span className="cursor">▶</span>배합목적
          </h4>
          <ul className="ing-detail-purpose-list">
            {ingredient.purposes.map((purpose) => (
              <li key={purpose.name}>
                <b>{purpose.name}</b> — {purpose.description}
              </li>
            ))}
          </ul>
        </section>
      )}

      {ingredient.relations.length > 0 && (
        <section className="ing-detail-section">
          <h4 className="ing-detail-title">
            <span className="cursor">▶</span>다른 성분과의 궁합
          </h4>
          <ul className="ing-detail-purpose-list">
            {ingredient.relations.map((relation, i) => (
              <li key={i}>
                <b>{relation.relation_type}</b> · {relation.related_ingredient_name}
                {relation.user_message && <> — {relation.user_message}</>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {combo_recommendation && (
        <section className="ing-detail-section">
          <h4 className="ing-detail-title">
            <span className="cursor">▶</span>궁합 팁
          </h4>
          <p>{combo_recommendation}</p>
        </section>
      )}
    </div>
  );
}
