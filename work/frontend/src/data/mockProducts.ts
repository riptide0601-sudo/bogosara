/**
 * 검색 결과 목(mock) 데이터.
 * 백엔드 성분 검색 API가 아직 없어서, 검색어와 무관하게 이 배열을 결과로 보여준다.
 * (App.tsx의 runSearch 참고 — 데모용으로 검색어에 "없음"이 포함되면 빈 결과를 흉내낸다)
 */
export interface Product {
  id: string;
  name: string;
  brand: string;
  summary: string;
}

export const MOCK_PRODUCTS: Product[] = [
  { id: 'p1', name: '수분진정크림', brand: '그린무드', summary: '주의 성분 0개 · 보습 위주' },
  { id: 'p2', name: '저자극 선크림 SPF50+', brand: '선데이랩', summary: '주의 성분 1개 · 자외선 차단' },
  { id: 'p3', name: '판테놀 카밍 토너', brand: '포레스트베리', summary: '주의 성분 0개 · 진정 위주' },
  { id: 'p4', name: '비타민C 앰플', brand: '글로우무드', summary: '주의 성분 2개 · 브라이트닝' },
  { id: 'p5', name: '약산성 클렌징 폼', brand: '퓨어데이즈', summary: '주의 성분 0개 · 저자극 세안' },
  { id: 'p6', name: '센텔라 리페어 크림', brand: '리페어랩', summary: '주의 성분 1개 · 재생·진정' },
  { id: 'p7', name: '히알루론산 세럼', brand: '모먼트스킨', summary: '주의 성분 0개 · 고보습' },
  { id: 'p8', name: '레티놀 나이트 크림', brand: '나잇모드', summary: '주의 성분 3개 · 주름개선(자극 주의)' },
];
