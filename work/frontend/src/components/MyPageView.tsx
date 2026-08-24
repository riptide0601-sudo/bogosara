import { useState, type KeyboardEvent } from 'react';
import {
  MOCK_SAVED_RESULTS,
  MOCK_SKIN_PROFILE,
  MOCK_USER,
  SKIN_TYPE_OPTIONS,
  type SavedResult,
} from '../data/myPage';
import '../MyPageView.css';

interface MyPageViewProps {
  onBack: () => void;
  /** 저장한 결과 카드를 클릭하면 App.tsx가 이 결과를 ResultView로 이어준다. */
  onSelectSavedResult: (result: SavedResult) => void;
}

const GRADE_LABEL: Record<SavedResult['grade'], string> = {
  star: '베스트',
  good: '순한 편',
  base: '주의 필요',
};

/**
 * 마이페이지 — 회원정보 / 저장한 결과 / 나의 피부 프로필·주의 성분 / 설정 4개 섹션.
 * 오버레이가 아니라 ResultView와 동일한 "페이지 전체 전환" 패턴을 쓴다 — 내용이 길어
 * 스크롤이 깊고, 저장한 결과 카드에서 다시 ResultView로 더 들어갈 수 있어야 하기 때문
 * (App.tsx의 resultRequest/ mypageOpen 상태 참고).
 *
 * 로그인/회원가입은 아직 없다(App.tsx·CLAUDE.md 참고) — 여기 보이는 회원정보·저장한 결과·
 * 피부 프로필은 전부 목 데이터이고, "로그인 연동 준비 중"인 액션(로그아웃/회원 탈퇴/정보 수정)은
 * 비활성 처리해뒀다. 피부 프로필·알림 설정은 이 화면 안에서만 로컬 상태로 바뀌고 새로고침하면
 * 초기 목값으로 돌아간다 — 실제 저장은 백엔드 연동 후에 붙는다.
 */
export default function MyPageView({ onBack, onSelectSavedResult }: MyPageViewProps) {
  const [savedResults, setSavedResults] = useState<SavedResult[]>(MOCK_SAVED_RESULTS);
  const [skinTypes, setSkinTypes] = useState<string[]>(MOCK_SKIN_PROFILE.skinTypes);
  const [watchedIngredients, setWatchedIngredients] = useState<string[]>(MOCK_SKIN_PROFILE.watchedIngredients);
  const [ingredientInput, setIngredientInput] = useState('');
  const [notifyAlerts, setNotifyAlerts] = useState(true);

  const toggleSkinType = (type: string) => {
    setSkinTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]));
  };

  const addWatchedIngredient = () => {
    const value = ingredientInput.trim();
    if (!value || watchedIngredients.includes(value)) {
      setIngredientInput('');
      return;
    }
    setWatchedIngredients((prev) => [...prev, value]);
    setIngredientInput('');
  };

  const handleIngredientKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addWatchedIngredient();
    }
  };

  const removeWatchedIngredient = (value: string) => {
    setWatchedIngredients((prev) => prev.filter((v) => v !== value));
  };

  const unsaveResult = (id: string) => {
    setSavedResults((prev) => prev.filter((r) => r.id !== id));
  };

  return (
    <div className="mypage-view">
      <header className="result-topbar">
        <button type="button" className="result-back-btn" onClick={onBack}>
          <span className="cursor">◀</span>홈으로
        </button>
      </header>

      <h1 className="mypage-title">
        <span className="cursor">▶</span>마이페이지
      </h1>

      {/* ---- 회원정보 ---- */}
      <section className="mypage-section" aria-labelledby="mypage-account-heading">
        <h2 className="mypage-section-title" id="mypage-account-heading">
          회원정보
        </h2>
        <div className="mypage-account-card">
          <div className="mypage-account-row">
            <span className="mypage-account-label">닉네임</span>
            <span className="mypage-account-value">{MOCK_USER.nickname}</span>
          </div>
          <div className="mypage-account-row">
            <span className="mypage-account-label">이메일</span>
            <span className="mypage-account-value">{MOCK_USER.email}</span>
          </div>
          <div className="mypage-account-row">
            <span className="mypage-account-label">가입일</span>
            <span className="mypage-account-value">{MOCK_USER.joinedAt}</span>
          </div>
          <p className="mypage-demo-note">체험용 데모 계정이에요 · 로그인/회원가입 연동 준비 중</p>
          <button type="button" className="mypage-ghost-btn" disabled title="로그인 연동 준비 중">
            회원정보 수정
          </button>
        </div>
      </section>

      {/* ---- 저장한 결과 ---- */}
      <section className="mypage-section" aria-labelledby="mypage-saved-heading">
        <h2 className="mypage-section-title" id="mypage-saved-heading">
          저장한 결과
          <span className="mypage-section-count">{savedResults.length}개</span>
        </h2>

        {savedResults.length === 0 ? (
          <div className="results-empty">
            <p>아직 저장한 결과가 없어요.</p>
            <p className="results-empty-sub">전성분 결과 화면에서 저장하면 여기에 모여요.</p>
          </div>
        ) : (
          <div className="mypage-saved-grid">
            {savedResults.map((result) => (
              <div className="mypage-saved-card" key={result.id}>
                <button
                  type="button"
                  className="mypage-saved-card-remove"
                  onClick={() => unsaveResult(result.id)}
                  aria-label={`${result.productName} 저장 해제`}
                  title="저장 해제"
                >
                  ✕
                </button>
                <button type="button" className="mypage-saved-card-main" onClick={() => onSelectSavedResult(result)}>
                  <span className={`ing-badge ing-badge--${result.grade} mypage-saved-badge`}>
                    {GRADE_LABEL[result.grade]}
                  </span>
                  <span className="mypage-saved-brand">{result.brand}</span>
                  <span className="mypage-saved-name">{result.productName}</span>
                  <span className="mypage-saved-meta">
                    주의 성분 {result.cautionCount}개 · {result.savedAt} 저장
                  </span>
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ---- 나의 피부 프로필 · 주의 성분 ---- */}
      <section className="mypage-section" aria-labelledby="mypage-skin-heading">
        <h2 className="mypage-section-title" id="mypage-skin-heading">
          나의 피부 프로필 · 주의 성분
        </h2>
        <p className="mypage-section-desc">
          등록해두면 다음 검색·스캔 결과에서 해당 성분이 나올 때 먼저 표시해줄 예정이에요.
        </p>

        <div className="mypage-profile-card">
          <p className="mypage-profile-label">피부 타입 (복수 선택 가능)</p>
          <div className="mypage-chip-row">
            {SKIN_TYPE_OPTIONS.map((type) => (
              <button
                key={type}
                type="button"
                className={`mypage-chip${skinTypes.includes(type) ? ' is-active' : ''}`}
                aria-pressed={skinTypes.includes(type)}
                onClick={() => toggleSkinType(type)}
              >
                {type}
              </button>
            ))}
          </div>

          <p className="mypage-profile-label mypage-profile-label--spaced">주의하고 싶은 성분</p>
          <div className="mypage-chip-row">
            {watchedIngredients.map((ingredient) => (
              <span className="mypage-chip mypage-chip--tag" key={ingredient}>
                {ingredient}
                <button
                  type="button"
                  className="mypage-chip-remove"
                  onClick={() => removeWatchedIngredient(ingredient)}
                  aria-label={`${ingredient} 삭제`}
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
          <div className="mypage-ingredient-add">
            <input
              type="text"
              className="mypage-ingredient-input"
              placeholder="예: 파라벤"
              value={ingredientInput}
              onChange={(e) => setIngredientInput(e.target.value)}
              onKeyDown={handleIngredientKeyDown}
              aria-label="주의 성분 추가"
            />
            <button type="button" className="mypage-ghost-btn" onClick={addWatchedIngredient}>
              추가
            </button>
          </div>
          <p className="mypage-demo-note">지금은 이 화면 안에서만 임시로 기억돼요 · 로그인 연동 후 계정에 저장돼요</p>
        </div>
      </section>

      {/* ---- 설정 ---- */}
      <section className="mypage-section" aria-labelledby="mypage-settings-heading">
        <h2 className="mypage-section-title" id="mypage-settings-heading">
          설정
        </h2>
        <div className="mypage-settings-card">
          <button
            type="button"
            className="mypage-toggle-row"
            role="switch"
            aria-checked={notifyAlerts}
            onClick={() => setNotifyAlerts((v) => !v)}
          >
            <span className={`mypage-toggle-box${notifyAlerts ? ' is-on' : ''}`} aria-hidden="true">
              {notifyAlerts ? '✓' : ''}
            </span>
            <span className="mypage-toggle-text">
              <span className="mypage-toggle-title">주의 성분 알림 받기</span>
              <span className="mypage-toggle-sub">등록한 주의 성분이 검색·스캔 결과에 나오면 알려줘요.</span>
            </span>
          </button>

          <div className="mypage-settings-divider" role="separator" />

          <button type="button" className="mypage-settings-link" disabled title="준비 중">
            이용약관
          </button>
          <button type="button" className="mypage-settings-link" disabled title="준비 중">
            개인정보처리방침
          </button>
          <div className="mypage-settings-version">보고사라 v0.1.0 (데모)</div>

          <div className="mypage-settings-divider" role="separator" />

          <button type="button" className="mypage-ghost-btn mypage-ghost-btn--danger" disabled title="로그인 연동 준비 중">
            로그아웃
          </button>
          <button type="button" className="mypage-settings-link mypage-settings-link--danger" disabled title="로그인 연동 준비 중">
            회원 탈퇴
          </button>
        </div>
      </section>
    </div>
  );
}
