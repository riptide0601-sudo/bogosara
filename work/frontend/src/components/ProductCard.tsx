import type { Product } from '../data/mockProducts';

interface ProductCardProps {
  product: Product;
  onSelect?: (product: Product) => void;
}

/**
 * 검색 결과 제품 카드.
 * 썸네일은 실제 이미지 대신 단색 배경 + 이니셜로 만든 플레이스홀더.
 * onSelect가 있으면 클릭 시 성분 결과 화면(ResultView)으로 이어진다 (App.tsx 참고).
 */
export default function ProductCard({ product, onSelect }: ProductCardProps) {
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
        <span className="product-thumb-mono">{product.name.charAt(0)}</span>
      </span>
      <span className="product-info">
        <span className="product-brand">{product.brand}</span>
        <span className="product-name">{product.name}</span>
        <span className="product-summary">{product.summary}</span>
      </span>
    </button>
  );
}
