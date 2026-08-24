import { useState } from 'react';

interface RawIngredientsPanelProps {
  rawIngredients: string;
}

/**
 * 카드 뒷면 맨 아래의 원문 전성분표 접힘 보기.
 * "임의 판단이 아니라 실제 표기를 근거로 한다"는 신뢰 장치 — 기본은 접혀 있다.
 */
export default function RawIngredientsPanel({ rawIngredients }: RawIngredientsPanelProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="raw-toggle-block">
      <button type="button" className="ing-more-toggle" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
        {expanded ? '원문 전성분표 접기' : '원문 전성분표 보기'}
      </button>
      {expanded && <p className="raw-panel-text">{rawIngredients}</p>}
    </div>
  );
}
