import { useState } from 'react';
import type { Ingredient, IngredientResultProduct } from '../data/ingredientResult';
import type { SkinRiskInfo } from './ResultView';
import ResultSummaryPanel from './ResultSummaryPanel';
import IngredientList from './IngredientList';
import IngredientDetail from './IngredientDetail';
import RawIngredientsPanel from './RawIngredientsPanel';

interface ResultCardProps {
  product: IngredientResultProduct;
  ingredients: Ingredient[];
  /** 스캔(OCR)으로 들어왔으면 제품명 대신 "스캔한 제품"으로 표시한다 (ResultSummaryPanel 참고). */
  isScan: boolean;
  /** 마이페이지 피부 타입 ↔ 이 제품 위험 성분 연동 결과 (ResultView.tsx에서 조회). */
  skinRisk: SkinRiskInfo;
}

/**
 * 결과 화면 오른쪽 — 카드 형태로, 앞면(요약)을 클릭하면 뒤집혀서 뒷면(전성분 나열+설명)이 보인다.
 * 두 면은 절대 위치로 겹쳐 있고(backface-visibility: hidden), 카드 자체 높이는 고정폭이라
 * 뒷면(리스트가 긴 쪽)은 내부 스크롤로 담는다 (ResultView.css 참고).
 *
 * 뒷면 안에서 한 단계 더 들어가는 상태도 있다 — 전성분 목록에서 성분 하나를 클릭하면
 * 그 성분의 상세 뷰(IngredientDetail)가 뒷면 전체를 차지한다. 이 상태는 `selectedIngredient`로
 * 관리하며, 카드가 앞면으로 뒤집힐 때는 항상 초기화해 다음에 뒷면을 다시 열면 목록부터 보인다.
 *
 * 앞면의 "핵심 성분" 칩(ResultSummaryPanel)을 클릭해도 같은 상세 뷰로 들어올 수 있다 — 이때는
 * 목록을 거치지 않고 바로 왔으므로, 뒤로가기도 목록이 아니라 곧장 앞면(요약)으로 돌아가야 한다.
 * `ingredientEntryPoint`로 두 진입 경로('list' / 'chip')를 구분해 handleBackNav의 동작과
 * 상세 뷰의 "뒤로" 버튼 라벨을 갈라 보여준다.
 */
export default function ResultCard({ product, ingredients, isScan, skinRisk }: ResultCardProps) {
  const [flipped, setFlipped] = useState(false);
  const [selectedIngredient, setSelectedIngredient] = useState<Ingredient | null>(null);
  const [ingredientEntryPoint, setIngredientEntryPoint] = useState<'list' | 'chip' | null>(null);
  const totalCount = ingredients.length;

  const flipToBack = () => setFlipped(true);
  const flipToFront = () => {
    setFlipped(false);
    setSelectedIngredient(null);
    setIngredientEntryPoint(null);
  };

  const handleFrontKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      flipToBack();
    }
  };

  const handleSelectFromList = (ingredient: Ingredient) => {
    setSelectedIngredient(ingredient);
    setIngredientEntryPoint('list');
  };

  /** "핵심 성분" 칩(ResultSummaryPanel)에서 이름으로 넘어온 클릭 — 전성분 배열에서 같은
   * 이름의 성분을 찾아 카드를 뒤집고 곧장 상세 뷰를 연다. */
  const handleSelectFromChip = (name: string) => {
    const ingredient = ingredients.find((i) => i.name_kr === name);
    if (!ingredient) return;
    setSelectedIngredient(ingredient);
    setIngredientEntryPoint('chip');
    flipToBack();
  };

  // 뒷면 상단 "◀" 버튼 — 상세 뷰가 열려 있으면 목록에서 왔을 땐 목록으로, 칩에서 왔을 땐
  // 목록을 거치지 않고 곧장 앞면(요약)으로. 상세 뷰가 없으면 그냥 앞면으로.
  const handleBackNav = () => {
    if (selectedIngredient) {
      if (ingredientEntryPoint === 'chip') {
        flipToFront();
      } else {
        setSelectedIngredient(null);
        setIngredientEntryPoint(null);
      }
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
          <ResultSummaryPanel
            product={product}
            totalCount={totalCount}
            isScan={isScan}
            skinRisk={skinRisk}
            isFlipped={flipped}
            onFlip={flipToBack}
            onSelectIngredient={handleSelectFromChip}
          />
        </div>

        {/* 뒷면: 전성분 나열 + 배합목적 설명. 성분을 클릭하면 상세 뷰가 이 면 전체를 차지한다. */}
        <div className="flip-card-face flip-card-back">
          {selectedIngredient ? (
            <IngredientDetail
              ingredient={selectedIngredient}
              onBack={handleBackNav}
              backLabel={ingredientEntryPoint === 'chip' ? '요약으로' : undefined}
            />
          ) : (
            <>
              <button type="button" className="flip-back-btn" onClick={handleBackNav}>
                <span className="cursor">◀</span>요약으로
              </button>
              <IngredientList ingredients={ingredients} onSelect={handleSelectFromList} />
              <RawIngredientsPanel rawIngredients={product.raw_ingredients} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
