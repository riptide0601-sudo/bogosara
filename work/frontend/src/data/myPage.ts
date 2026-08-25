export interface SavedResult {
  /** 실제 백엔드 product_id — 클릭 시 ResultView에서 이 id로 /products/{id}를 다시 조회한다. */
  id: string;
  productName: string;
  brand: string;
  grade: 'star' | 'good' | 'base';
  cautionCount: number;
  savedAt: string;
}

export interface SkinProfile {
  skinTypes: string[];
  watchedIngredients: string[];
}

export interface MockUser {
  nickname: string;
  email: string;
  joinedAt: string;
}

/** app/skin_fit.py가 다루는 피부 타입 네 가지 (README "피부 타입별 위험/궁합 성분 탐지" 참고). */
export const SKIN_TYPE_OPTIONS = ['지성', '복합성', '건성', '민감성'];

export const MOCK_USER: MockUser = {
  nickname: '보고사라',
  email: 'demo@bogosara.app',
  joinedAt: '2026.01.15',
};

export const MOCK_SKIN_PROFILE: SkinProfile = {
  skinTypes: ['건성', '민감성'],
  watchedIngredients: ['파라벤', '향료'],
};

export const MOCK_SAVED_RESULTS: SavedResult[] = [
  {
    id: 'p-1d9314842bc4',
    productName: 'AHC 프로샷 글루타 브라이트 인트라 세럼 40ml',
    brand: 'AHC',
    grade: 'star',
    cautionCount: 1,
    savedAt: '2026.08.10',
  },
  {
    id: 'p-76d4e4a3eb49',
    productName: 'VT 리들샷 100 에센스 30ml',
    brand: 'VT',
    grade: 'good',
    cautionCount: 0,
    savedAt: '2026.08.05',
  },
  {
    id: 'p-b400dc62b46f',
    productName: '[단독기획] 토리든 밸런스풀 시카 진정 크림 80ml 기획',
    brand: '토리든',
    grade: 'good',
    cautionCount: 0,
    savedAt: '2026.07.28',
  },
];
