export interface Product {
  id: string;
  name: string;
  brand: string;
  summary: string;
}

/** 검색 API 미연동 화면(추천 제품 등)에서 쓰는 목 데이터 — product_id는 로컬 DB에 실재하는 제품이라
 * 클릭하면 실제 /products/{id} 결과로 이어진다. */
export const MOCK_PRODUCTS: Product[] = [
  {
    id: 'p-1d9314842bc4',
    name: 'AHC 프로샷 글루타 브라이트 인트라 세럼 40ml',
    brand: 'AHC',
    summary: '나이아신아마이드로 결 정돈, 스쿠알란으로 유수분 밸런스를 잡아주는 세럼.',
  },
  {
    id: 'p-76d4e4a3eb49',
    name: 'VT 리들샷 100 에센스 30ml',
    brand: 'VT',
    summary: '마이크로니들 성분감으로 유수분 라인을 정돈해주는 에센스.',
  },
  {
    id: 'p-b400dc62b46f',
    name: '[단독기획] 토리든 밸런스풀 시카 진정 크림 80ml 기획',
    brand: '토리든',
    summary: '시카 성분으로 예민해진 피부를 진정시켜주는 크림.',
  },
  {
    id: 'p-25071cd9a85a',
    name: 'VT 피디알엔 에센스 100 30ml',
    brand: 'VT',
    summary: '보습 유연 성분 위주로 구성된 산뜻한 에센스.',
  },
];
