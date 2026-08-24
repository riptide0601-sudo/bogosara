import { useState } from 'react';
import type { Ingredient, IngredientResultProduct } from '../data/ingredientResult';
import ResultSummaryPanel from './ResultSummaryPanel';
import IngredientList from './IngredientList';
import IngredientDetail from './IngredientDetail';
import RawIngredientsPanel from './RawIngredientsPanel';

interface ResultCardProps {
  product: IngredientResultProduct;
  ingredients: Ingredient[];
  /** 스캔(OCR)으로 들어왔으면 제품명 대신 "스캔한 제품"으로 표시한다 (ResultSummaryPanel 참고). */
  isScan: boolean;
}

/**
 * 결과 화면 오른쪽 — 카드 형태로, 앞면(요약)을 클릭하면 뒤집혀서 뒷면(전성분 나열+설명)이 보인다.
 * 두 면은 절대 위치로 겹쳐 있고(backface-visibility: hidden), 카드 자체 높이는 고정폭이라
 * 뒷면(리스트가 긴 쪽)은 내부 스크롤로 담는다 (ResultView.css 참고).
 *
 * 뒷면 안에서 한 단계 더 들어가는 상태도 있다 — 전성분 목록에서 성분 하나를 클릭하면
 * 그 성분의 상세 뷰(IngredientDetail)가 뒷면 전체를 차지한다. 이 상태는 `selectedIngredient`로
 * 관리하며, 카드가 앞면으로 뒤집힐 때는 항상 초기화해 다음에 뒷면을 다시 열면 목록부터 보인다.
 */
export default function ResultCard({ product, ingredients, isScan }: ResultCardProps) {
  const [flipped, setFlipped] = useState(false);
  const [selectedIngredient, setSelectedIngredient] = useState<Ingredient | null>(null);
  const totalCount = ingredients.length;

  const flipToBack = () => setFlipped(true);
  const flipToFront = () => {
    setFlipped(false);
    setSelectedIngredient(null);
  };

  const handleFrontKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      flipToBack();
    }
  };

  // 뒷면 상단 "◀" 버튼 — 상세 뷰가 열려 있으면 한 단계만 목록으로, 아니면 앞면으로 되돌아간다.
  const handleBackNav = () => {
    if (selectedIngredient) {
      setSelectedIngredient(null);
    } else {
      flipToFront();
    }
  };

  return (
    <div className={`flip-card${flipped ? ' is-flipped' : ''}`}>
      <div className="flip-card-inner">
        {/* 앞면: 요약 페이지 */}
        <div
          className="flip-card-face flip-card-front"
          role="button"
          tabIndex={0}
          aria-expanded={flipped}
          aria-label={`카드를 눌러 전성분 ${totalCount}개 보기`}
          onClick={flipToBack}
          onKeyDown={handleFrontKeyDown}
        >
          <ResultSummaryPanel product={product} totalCount={totalCount} isScan={isScan} />
        </div>

        {/* 뒷면: 전성분 나열 + 배합목적 설명. 성분을 클릭하면 상세 뷰가 이 면 전체를 차지한다. */}
        <div className="flip-card-face flip-card-back">
          {selectedIngredient ? (
            <IngredientDetail ingredient={selectedIngredient} onBack={handleBackNav} />
          ) : (
            <>
              <button type="button" className="flip-back-btn" onClick={handleBackNav}>
                <span className="cursor">◀</span>요약으로
              </button>
              <IngredientList ingredients={ingredients} onSelect={setSelectedIngredient} />
              <RawIngredientsPanel rawIngredients={product.raw_ingredients} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
