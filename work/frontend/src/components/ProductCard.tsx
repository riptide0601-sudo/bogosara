import { useState } from 'react';
import type { Product } from '../data/mockProducts';

interface ProductCardProps {
  product: Product;
  onSelect?: (product: Product) => void;
}

/**
 * 검색 결과 제품 카드.
 * product.image_url이 있으면 실제 제품 사진을, 없거나 로드 실패하면 단색 배경 + 이니셜
 * 플레이스홀더를 보여준다 (scripts/backfill_product_images.py로 채운 제품만 사진이 있음).
 * onSelect가 있으면 클릭 시 성분 결과 화면(ResultView)으로 이어진다 (App.tsx 참고).
 */
export default function ProductCard({ product, onSelect }: ProductCardProps) {
  const [imgFailed, setImgFailed] = useState(false);

  const handleClick = () => {
    if (onSelect) {
      onSelect(product);
      return;
    }
    // onSelect가 없을 때(App에 연결 안 된 단독 사용)를 위한 폴백 스텁
    console.log('[보고사라][제품 카드 스텁] 클릭:', product.name, `(${product.brand})`);
  };

  return (
    <button type="button" className="product-card" onClick={handleClick}>
      <span className="product-thumb" aria-hidden="true">
        {product.image_url && !imgFailed ? (
          <img
            className="product-thumb-img"
            src={product.image_url}
            alt=""
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <span className="product-thumb-mono">{product.name.charAt(0)}</span>
        )}
      </span>
      <span className="product-info">
        <span className="product-brand">{product.brand}</span>
        <span className="product-name">{product.name}</span>
        <span className="product-summary">{product.summary}</span>
      </span>
    </button>
  );
}
