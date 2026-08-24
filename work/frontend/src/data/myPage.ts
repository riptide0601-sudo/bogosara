import type { IngredientGrade } from './ingredientResult';

/**
 * 마이페이지 목(mock) 데이터.
 * 로그인/회원가입이 아직 없어서(App.tsx 참고), 실제로는 "로그인 후 이 결과를 저장" 흐름이지만
 * 지금은 이미 로그인된 데모 계정을 가정하고 화면을 완성해둔다.
 * TODO: 실제 로그인 연동 후 — 이 파일의 값들을 전부 백엔드 응답(회원정보 / 저장한 결과 / 프로필 설정)으로 교체.
 */

export interface MyPageUser {
  nickname: string;
  email: string;
  joinedAt: string; // YYYY-MM-DD
}

export const MOCK_USER: MyPageUser = {
  nickname: '보고사라',
  email: 'bogosara.demo@example.com',
  joinedAt: '2026-03-02',
};

/** 검색/스캔 결과 화면(ResultView)에서 "저장" 했다고 가정한 항목들. */
export interface SavedResult {
  id: string;
  productName: string;
  brand: string;
  grade: IngredientGrade;
  cautionCount: number;
  savedAt: string; // YYYY-MM-DD
}

export const MOCK_SAVED_RESULTS: SavedResult[] = [
  { id: 's1', productName: '발효 펩타이드 세럼', brand: '퍼먼트랩', grade: 'star', cautionCount: 0, savedAt: '2026-08-12' },
  { id: 's2', productName: '저자극 선크림 SPF50+', brand: '선데이랩', grade: 'good', cautionCount: 1, savedAt: '2026-08-05' },
  { id: 's3', productName: '레티놀 나이트 크림', brand: '나잇모드', grade: 'base', cautionCount: 3, savedAt: '2026-07-28' },
];

/** 선택 가능한 피부 타입 태그(다중 선택). */
export const SKIN_TYPE_OPTIONS = ['건성', '지성', '복합성', '민감성', '트러블성', '수분부족지성'] as const;

/** 나의 피부 프로필 — 자주 겪는 피부 타입 + 직접 등록한 "주의하고 싶은 성분" 목록.
 * 등록해두면 이후 검색/스캔 결과에서 이 성분이 나올 때 자동으로 주의 표시를 해주는 걸 목표로 한다
 * (지금은 아직 ResultView와 연동되지 않은 마이페이지 전용 설정 화면). */
export interface SkinProfile {
  skinTypes: string[];
  watchedIngredients: string[];
}

export const MOCK_SKIN_PROFILE: SkinProfile = {
  skinTypes: ['민감성'],
  watchedIngredients: ['향료', '알코올(에탄올)'],
};
