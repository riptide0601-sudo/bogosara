import type { Ingredient } from '../data/ingredientResult';
import { getIngredientBadge } from '../data/ingredientGrade';

interface IngredientRowProps {
  ingredient: Ingredient;
  onSelect: (ingredient: Ingredient) => void;
}

/**
 * 전성분 리스트 한 행 — 등급 배지 + 성분명(국/영문) + 배합목적 한 줄 + (규제 성분이면) 경고 pill.
 * 클릭(또는 Enter/Space)하면 이 성분의 상세 뷰(IngredientDetail)가 카드 뒷면 전체를 차지한다.
 */
export default function IngredientRow({ ingredient, onSelect }: IngredientRowProps) {
  const badge = getIngredientBadge(ingredient);
  const reason = ingredient.llm_summary.usage_reason_text;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(ingredient);
    }
  };

  return (
    <div
      className="ing-row"
      role="button"
      tabIndex={0}
      onClick={() => onSelect(ingredient)}
      onKeyDown={handleKeyDown}
      aria-label={`${ingredient.name_kr} 자세히 보기`}
    >
      <span className={`ing-badge ${badge.className}`}>{badge.label}</span>
      <div className="ing-main">
        <p className="ing-name">
          {ingredient.name_kr} <span className="ing-name-en">{ingredient.name_en}</span>
        </p>
        {reason && <p className="ing-reason">{reason}</p>}
        {ingredient.restricted && (
          <span className="ing-pill" title={ingredient.restricted.limit_cond}>
            ⚠ {ingredient.restricted.regulate_type}
          </span>
        )}
      </div>
      <span className="ing-row-arrow cursor" aria-hidden="true">▶</span>
    </div>
  );
}
