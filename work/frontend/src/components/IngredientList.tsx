import { useState } from 'react';
import type { Ingredient, IngredientGrade } from '../data/ingredientResult';
import IngredientRow from './IngredientRow';

interface IngredientListProps {
  ingredients: Ingredient[];
  onSelect: (ingredient: Ingredient) => void;
}

const GRADE_ORDER: Record<IngredientGrade, number> = { star: 0, good: 1, base: 2 };

/**
 * 전체 성분 + 배합목적 나열.
 * star → good → base 순으로 정렬하고, 슈퍼스타/구디는 항상 펼쳐서 보여준다.
 * base(기본) 성분은 개수가 많은 편이라 기본은 접어두고 "더보기" 토글로 펼친다.
 */
export default function IngredientList({ ingredients, onSelect }: IngredientListProps) {
  const [baseExpanded, setBaseExpanded] = useState(false);

  const sorted = [...ingredients].sort((a, b) => {
    const byGrade = GRADE_ORDER[a.display_grade] - GRADE_ORDER[b.display_grade];
    return byGrade !== 0 ? byGrade : a.label_rank - b.label_rank;
  });

  const primary = sorted.filter((ingredient) => ingredient.display_grade !== 'base');
  const base = sorted.filter((ingredient) => ingredient.display_grade === 'base');

  return (
    <section className="ing-list-section" aria-label="전성분 목록">
      <h2 className="ing-list-title">
        <span className="cursor">▶</span>전성분 · 배합목적
      </h2>

      <div className="ing-list">
        {primary.map((ingredient) => (
          <IngredientRow key={ingredient.name_en} ingredient={ingredient} onSelect={onSelect} />
        ))}
      </div>

      {base.length > 0 && (
        <>
          <div className={`ing-list ing-list--base${baseExpanded ? ' expanded' : ''}`}>
            {base.map((ingredient) => (
              <IngredientRow key={ingredient.name_en} ingredient={ingredient} onSelect={onSelect} />
            ))}
          </div>
          <button
            type="button"
            className="ing-more-toggle"
            aria-expanded={baseExpanded}
            onClick={() => setBaseExpanded((expanded) => !expanded)}
          >
            {baseExpanded ? '기본 성분 접기' : `기본 성분 더보기 (${base.length}개)`}
          </button>
        </>
      )}
    </section>
  );
}
