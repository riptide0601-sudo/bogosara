import type { IngredientResultRequest } from '../data/ingredientResult';
import type { Product } from '../data/mockProducts';

interface PhotoPanelProps {
  request: IngredientResultRequest;
  productName: string;
  /** app/similarity.py 코사인 유사도 기준 Top3 — ResultView가 IngredientResult에서 그대로 전달한다. */
  recommendedProducts: Product[];
  /** 추천 제품 클릭 시 그 제품의 결과 화면으로 이동 (App.tsx의 handleSelectProduct). */
  onSelectProduct: (product: Product) => void;
}

/**
 * 결과 화면 왼쪽 — 검색으로 왔으면 제품 썸네일(플레이스홀더), 스캔으로 왔으면
 * 실제로 촬영한 뒷면 사진을 보여준다 (request.imageDataUrl, ScanOverlay의 캡처 결과).
 * 사진 아래에는 제품명 대신(캡션 없음) 유사도 Top3(app/similarity.py 코사인 유사도)를 나열한다 — 예전엔 사진
 * 상자를 뒤집어서 보여줬는데, 다시 뒤집기 없는 단순한 목록으로 되돌렸다. 항목은 "브랜드 · 이름"을
 * 한 줄로 붙여서(브랜드/이름을 두 줄로 나누지 않음) 목록 전체 높이를 압축했다 — 그래야 세 번째
 * 항목의 아래쪽이 오른쪽 성분 카드의 아래쪽과 맞춰진다 (ResultView.css 참고). 클릭하면 그
 * 제품의 결과 화면으로 넘어간다(onSelectProduct — App.tsx의 검색 결과 카드 클릭과 동일한 진입점).
 * 저장 버튼은 이 컴포넌트가 아니라 ResultView 상단 바에 있다 (사진 상자 오른쪽 선에
 * 맞춘 정사각형 버튼 — ResultView.tsx/ResultView.css 참고).
 */
export default function PhotoPanel({ request, productName, recommendedProducts, onSelectProduct }: PhotoPanelProps) {
  const isScan = request.source === 'scan';

  return (
    <div className="photo-panel">
      {isScan ? (
        <img className="photo-panel-img" src={request.imageDataUrl} alt="촬영한 전성분표 뒷면 사진" />
      ) : (
        <div className="photo-panel-placeholder" aria-hidden="true">
          <span className="photo-panel-mono">{productName.charAt(0)}</span>
        </div>
      )}

      {recommendedProducts.length > 0 && (
        <section className="photo-reco-section" aria-labelledby="photo-reco-title">
          <p className="photo-reco-title" id="photo-reco-title">
            <span className="cursor">▶</span>이런 제품은 어때요?
          </p>
          <ul className="photo-reco-list">
            {recommendedProducts.map((product) => (
              <li key={product.id}>
                <button type="button" className="photo-reco-item" onClick={() => onSelectProduct(product)}>
                  <span className="photo-reco-brand">{product.brand}</span>
                  <span className="photo-reco-sep" aria-hidden="true"> · </span>
                  <span className="photo-reco-name">{product.name}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
