import { useEffect, useRef, useState, type RefObject } from 'react';
import type { OcrTextRegion } from '../api';
import type { IngredientResultRequest } from '../data/ingredientResult';
import type { Product } from '../data/mockProducts';
import SaveIcon from '../icons/SaveIcon';

interface PhotoPanelProps {
  request: IngredientResultRequest;
  productName: string;
  /** data.product.image_url(api.ts가 절대 URL로 변환) — 검색 진입(source==='search')일 때만 쓰인다.
   * 스캔 진입은 항상 request.imageDataUrl(촬영한 사진)을 그대로 보여준다. */
  productImageUrl: string | null;
  /** app/similarity.py 코사인 유사도 기준 Top3 — ResultView가 IngredientResult에서 그대로 전달한다. */
  recommendedProducts: Product[];
  /** 추천 제품 클릭 시 그 제품의 결과 화면으로 이동 (App.tsx의 handleSelectProduct). */
  onSelectProduct: (product: Product) => void;
  /** 아래 저장 버튼 상태/핸들러 — 로그인·저장 로직은 ResultView가 그대로 들고 있고,
   * 이 컴포넌트는 표시와 클릭 전달만 한다. */
  saved: boolean;
  saving: boolean;
  saveError: string | null;
  onSaveClick: () => void;
}

interface HighlightRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * OCR이 인식한 줄(box_pct, 이미지 너비/높이 기준 0~1 비율)을 사진 위 형광펜 박스로 그린다.
 * 사진은 .photo-panel-img가 object-fit:cover로 표시돼서(원본 비율 3:4 상자에 꽉 채워 자름)
 * box_pct를 그대로 %로 쓸 수 없다 — cover가 실제로 얼마나 확대·크롭했는지를 img의
 * naturalWidth/Height(원본 픽셀)와 clientWidth/Height(화면에 그려진 크기)로 계산해서
 * 보정해야 사진 속 글자 위치와 형광펜 박스가 어긋나지 않는다.
 */
function PhotoHighlightLayer({
  regions,
  imgRef,
}: {
  regions: OcrTextRegion[];
  imgRef: RefObject<HTMLImageElement | null>;
}) {
  const [rects, setRects] = useState<HighlightRect[]>([]);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;

    const recompute = () => {
      const naturalW = img.naturalWidth;
      const naturalH = img.naturalHeight;
      const boxW = img.clientWidth;
      const boxH = img.clientHeight;
      if (!naturalW || !naturalH || !boxW || !boxH) return;

      // object-fit:cover 스케일 — 두 축 중 상자를 완전히 채우는 쪽(더 큰 배율)을 쓰고,
      // 남는 쪽은 중앙 기준으로 잘려나간다(브라우저 기본 object-position: 50% 50%).
      const scale = Math.max(boxW / naturalW, boxH / naturalH);
      const displayedW = naturalW * scale;
      const displayedH = naturalH * scale;
      const cropX = (displayedW - boxW) / 2;
      const cropY = (displayedH - boxH) / 2;

      setRects(
        regions.map(({ box_pct: [x1, y1, x2, y2] }) => ({
          left: ((x1 * displayedW - cropX) / boxW) * 100,
          top: ((y1 * displayedH - cropY) / boxH) * 100,
          width: (((x2 - x1) * displayedW) / boxW) * 100,
          height: (((y2 - y1) * displayedH) / boxH) * 100,
        })),
      );
    };

    if (img.complete) recompute();
    img.addEventListener('load', recompute);
    const resizeObserver = new ResizeObserver(recompute);
    resizeObserver.observe(img);
    return () => {
      img.removeEventListener('load', recompute);
      resizeObserver.disconnect();
    };
  }, [imgRef, regions]);

  if (rects.length === 0) return null;

  return (
    <div className="photo-panel-highlight-layer" aria-hidden="true">
      {rects.map((r, i) => (
        <span
          key={i}
          className="photo-panel-highlight"
          style={{ left: `${r.left}%`, top: `${r.top}%`, width: `${r.width}%`, height: `${r.height}%` }}
        />
      ))}
    </div>
  );
}

/**
 * 결과 화면 왼쪽 — 검색으로 왔으면 제품 썸네일(플레이스홀더), 스캔으로 왔으면
 * 실제로 촬영한 뒷면 사진을 보여준다 (request.imageDataUrl, ScanOverlay의 캡처 결과).
 * 스캔 사진 위에는 OCR이 인식한 줄마다 형광펜 박스를 얹는다(request.ocr.text_regions,
 * PhotoHighlightLayer 참고) — "여기서 전성분을 읽었다"를 사진에서 바로 보여주는 용도라
 * 성분 하나하나가 아니라 OCR이 잡은 줄 단위로 표시한다.
 * 사진 바로 아래엔 저장 버튼("내 화장품으로 저장"), 그 아래엔 제품명 대신(캡션 없음)
 * 유사도 Top3(app/similarity.py 코사인 유사도)를 나열한다 — 예전엔 사진 상자를 뒤집어서
 * 보여줬는데, 다시 뒤집기 없는 단순한 목록으로 되돌렸다. 항목은 "브랜드 · 이름"을
 * 한 줄로 붙여서(브랜드/이름을 두 줄로 나누지 않음) 목록 전체 높이를 압축했다. 클릭하면 그
 * 제품의 결과 화면으로 넘어간다(onSelectProduct — App.tsx의 검색 결과 카드 클릭과 동일한 진입점).
 */
export default function PhotoPanel({
  request,
  productName,
  productImageUrl,
  recommendedProducts,
  onSelectProduct,
  saved,
  saving,
  saveError,
  onSaveClick,
}: PhotoPanelProps) {
  const isScan = request.source === 'scan';
  const scanImgRef = useRef<HTMLImageElement>(null);
  const textRegions = isScan ? request.ocr.text_regions : [];

  return (
    <div className="photo-panel">
      {isScan ? (
        <div className="photo-panel-img-wrap">
          <img
            ref={scanImgRef}
            className="photo-panel-img"
            src={request.imageDataUrl}
            alt="촬영한 전성분표 뒷면 사진"
          />
          {textRegions.length > 0 && <PhotoHighlightLayer regions={textRegions} imgRef={scanImgRef} />}
        </div>
      ) : productImageUrl ? (
        <img className="photo-panel-img" src={productImageUrl} alt={productName} />
      ) : (
        <div className="photo-panel-placeholder" aria-hidden="true">
          <span className="photo-panel-mono">{productName.charAt(0)}</span>
        </div>
      )}

      {/* 로그인 상태면 바로 저장하고 .is-saved 톤으로 바뀌고, 비로그인이면 ResultView가
          로그인 팝업을 띄운다. */}
      <button
        type="button"
        className={`photo-save-btn${saved ? ' is-saved' : ''}`}
        onClick={onSaveClick}
        disabled={saving}
        aria-pressed={saved}
      >
        <SaveIcon />
        {saved ? '저장됨' : '내 화장품으로 저장'}
      </button>
      {saveError && (
        <p className="photo-save-error" role="alert">
          {saveError}
        </p>
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
