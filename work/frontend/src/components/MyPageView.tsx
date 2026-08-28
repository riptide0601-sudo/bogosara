import { useEffect, useState, type KeyboardEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../api/client';
import { getSkinProfile, listSavedResults, unsaveResult, updateMe, updateSkinProfile } from '../api/users';
import { deleteRoutineHistory, listRoutineHistory } from '../api/routine';
import type { RoutineHistoryRead, SkinProfile } from '../api/types';
import { SKIN_TYPE_OPTIONS, toSavedResult, type SavedResult } from '../data/myPage';
import CosmeticMascotIcon from '../icons/CosmeticMascotIcon';
import CreamJarIcon from '../icons/CreamJarIcon';
import CushionIcon from '../icons/CushionIcon';
import '../MyPageView.css';

interface MyPageViewProps {
  onBack: () => void;
  /** 저장한 결과 카드를 클릭하면 App.tsx가 이 결과를 ResultView로 이어준다. */
  onSelectSavedResult: (result: SavedResult) => void;
  /** "내 화장품 조합" 진입점 클릭 → App.tsx가 RoutineView로 전체 화면을 교체한다. */
  onOpenRoutine: () => void;
  /** "조합 기록" 카드 클릭 → App가 그 기록의 조합 분석을 보여주는 RoutineView로 이동한다. */
  onOpenRoutineHistory: (entry: RoutineHistoryRead) => void;
}

const GRADE_LABEL: Record<NonNullable<SavedResult['grade']>, string> = {
  star: '베스트',
  good: '순한 편',
  base: '주의 필요',
};

const GENDER_OPTIONS = ['여성', '남성'];

/** 화면 아래를 걸어다니는 캐릭터 3종(MyPagePage.tsx의 WALKING_MASCOTS)과 같은 아이콘 —
 * 회원정보에서 이 중 하나를 프로필 사진으로 고를 수 있다. */
const PROFILE_ICON_OPTIONS: { key: string; label: string; Icon: typeof CosmeticMascotIcon }[] = [
  { key: 'cosmetic', label: '화장품 캐릭터', Icon: CosmeticMascotIcon },
  { key: 'cream', label: '크림통 캐릭터', Icon: CreamJarIcon },
  { key: 'cushion', label: '쿠션 캐릭터', Icon: CushionIcon },
];

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return '네트워크 상태를 확인하고 다시 시도해주세요.';
}

type FetchStatus = 'loading' | 'done' | 'error';

/**
 * 마이페이지 — 회원정보 / 저장한 결과 / 나의 피부 프로필·주의 성분 / 설정 4개 섹션.
 * 오버레이가 아니라 ResultView와 동일한 "페이지 전체 전환" 패턴을 쓴다 (App.tsx 참고).
 *
 * App.tsx가 로그인 상태일 때만 이 화면을 띄우므로 useAuth().user는 항상 값이 있다고 가정한다.
 * 회원정보(닉네임/이메일/가입일/알림설정)는 AuthContext가 이미 들고 있어 별도 조회가 필요
 * 없고, 피부 프로필·저장한 결과만 이 화면에서 따로 불러온다. 각 섹션은 실패해도 서로에게
 * 영향을 주지 않도록 로딩/에러 상태를 독립적으로 관리한다.
 */
export default function MyPageView({
  onBack,
  onSelectSavedResult,
  onOpenRoutine,
  onOpenRoutineHistory,
}: MyPageViewProps) {
  const { user, setUser, logout } = useAuth();

  // ---- 저장한 결과 ----
  const [savedStatus, setSavedStatus] = useState<FetchStatus>('loading');
  const [savedResults, setSavedResults] = useState<SavedResult[]>([]);
  const [savedError, setSavedError] = useState<string | null>(null);

  // ---- 조합 기록 (한 줄 요약용 — 최근 저장 개수/날짜만 필요) ----
  const [routineHistory, setRoutineHistory] = useState<RoutineHistoryRead[]>([]);

  // ---- 피부 프로필 ----
  const [skinStatus, setSkinStatus] = useState<FetchStatus>('loading');
  const [skinProfile, setSkinProfile] = useState<SkinProfile | null>(null);
  const [skinLoadError, setSkinLoadError] = useState<string | null>(null);
  const [skinSaveError, setSkinSaveError] = useState<string | null>(null);
  const [ingredientInput, setIngredientInput] = useState('');

  // ---- 회원정보 수정 (닉네임/나이/성별을 한 번에 수정) ----
  const [editingNickname, setEditingNickname] = useState(false);
  const [nicknameDraft, setNicknameDraft] = useState(user?.nickname ?? '');
  const [ageDraft, setAgeDraft] = useState(user?.age != null ? String(user.age) : '');
  const [genderDraft, setGenderDraft] = useState<string | null>(user?.gender ?? null);
  const [profileIconDraft, setProfileIconDraft] = useState<string | null>(user?.profile_icon ?? null);
  const [savingNickname, setSavingNickname] = useState(false);
  const [nicknameError, setNicknameError] = useState<string | null>(null);

  // ---- 설정 ----
  const [notifySaving, setNotifySaving] = useState(false);
  const [notifyError, setNotifyError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    listSavedResults()
      .then((results) => {
        if (cancelled) return;
        setSavedResults(results.map(toSavedResult));
        setSavedStatus('done');
      })
      .catch((err) => {
        if (cancelled) return;
        setSavedError(errorMessage(err));
        setSavedStatus('error');
      });

    getSkinProfile()
      .then((profile) => {
        if (cancelled) return;
        setSkinProfile(profile);
        setSkinStatus('done');
      })
      .catch((err) => {
        if (cancelled) return;
        setSkinLoadError(errorMessage(err));
        setSkinStatus('error');
      });

    // 한 줄 요약(개수·최근 날짜)만 보여줄 거라 로딩/에러는 따로 안 다룬다 — 실패해도
    // 그냥 안 보이면 그만이라, 조합 화면(RoutineView)만큼 신경 쓸 정보가 아니다.
    listRoutineHistory()
      .then((results) => {
        if (cancelled) return;
        setRoutineHistory(results);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  if (!user) return null;

  // ---- 회원정보 수정 ----
  const startEditNickname = () => {
    setNicknameDraft(user.nickname);
    setAgeDraft(user.age != null ? String(user.age) : '');
    setGenderDraft(user.gender ?? null);
    setProfileIconDraft(user.profile_icon ?? null);
    setNicknameError(null);
    setEditingNickname(true);
  };

  const saveNickname = async () => {
    const value = nicknameDraft.trim();
    if (!value || savingNickname) return;
    const trimmedAge = ageDraft.trim();
    const age = trimmedAge ? Number(trimmedAge) : null;
    if (trimmedAge && (!Number.isInteger(age) || age! < 0 || age! > 120)) {
      setNicknameError('나이는 0~120 사이 숫자로 입력해주세요.');
      return;
    }
    setSavingNickname(true);
    setNicknameError(null);
    try {
      const updated = await updateMe({ nickname: value, age, gender: genderDraft, profile_icon: profileIconDraft });
      setUser(updated);
      setEditingNickname(false);
    } catch (err) {
      setNicknameError(errorMessage(err));
    } finally {
      setSavingNickname(false);
    }
  };

  // ---- 저장한 결과 ----
  const unsaveResultCard = async (id: string) => {
    const prev = savedResults;
    setSavedResults((list) => list.filter((r) => r.id !== id));
    setSavedError(null);
    try {
      await unsaveResult(id);
    } catch (err) {
      setSavedResults(prev);
      setSavedError(errorMessage(err));
    }
  };

  // ---- 조합 기록 ----
  const deleteRoutineHistoryCard = async (historyId: string) => {
    const prev = routineHistory;
    setRoutineHistory((list) => list.filter((h) => h.history_id !== historyId));
    try {
      await deleteRoutineHistory(historyId);
    } catch (err) {
      setRoutineHistory(prev);
      console.error('[보고사라][마이페이지] 조합 기록 삭제 실패', err);
    }
  };

  // ---- 피부 프로필 ----
  const toggleSkinType = (type: string) => {
    if (!skinProfile) return;
    const nextTypes = skinProfile.skin_types.includes(type)
      ? skinProfile.skin_types.filter((t) => t !== type)
      : [...skinProfile.skin_types, type];
    const prev = skinProfile;
    setSkinProfile({ ...skinProfile, skin_types: nextTypes });
    setSkinSaveError(null);
    updateSkinProfile({ skin_types: nextTypes })
      .then(setSkinProfile)
      .catch((err) => {
        setSkinProfile(prev);
        setSkinSaveError(errorMessage(err));
      });
  };

  const addWatchedIngredient = () => {
    if (!skinProfile) return;
    const value = ingredientInput.trim();
    setIngredientInput('');
    if (!value || skinProfile.watched_ingredients.includes(value)) return;

    const nextIngredients = [...skinProfile.watched_ingredients, value];
    const prev = skinProfile;
    setSkinProfile({ ...skinProfile, watched_ingredients: nextIngredients });
    setSkinSaveError(null);
    updateSkinProfile({ watched_ingredients: nextIngredients })
      .then(setSkinProfile)
      .catch((err) => {
        setSkinProfile(prev);
        setSkinSaveError(errorMessage(err));
      });
  };

  const handleIngredientKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addWatchedIngredient();
    }
  };

  const removeWatchedIngredient = (value: string) => {
    if (!skinProfile) return;
    const nextIngredients = skinProfile.watched_ingredients.filter((v) => v !== value);
    const prev = skinProfile;
    setSkinProfile({ ...skinProfile, watched_ingredients: nextIngredients });
    setSkinSaveError(null);
    updateSkinProfile({ watched_ingredients: nextIngredients })
      .then(setSkinProfile)
      .catch((err) => {
        setSkinProfile(prev);
        setSkinSaveError(errorMessage(err));
      });
  };

  // ---- 설정 ----
  const toggleNotifyAlerts = async () => {
    if (notifySaving) return;
    const prev = user;
    const next = !user.notify_alerts;
    setUser({ ...user, notify_alerts: next });
    setNotifySaving(true);
    setNotifyError(null);
    try {
      const updated = await updateMe({ notify_alerts: next });
      setUser(updated);
    } catch (err) {
      setUser(prev);
      setNotifyError(errorMessage(err));
    } finally {
      setNotifySaving(false);
    }
  };

  return (
    <div className="mypage-view">
      <header className="result-topbar">
        <button type="button" className="result-back-btn" onClick={onBack}>
          <span className="cursor">◀</span>뒤로가기
        </button>
      </header>

      <h1 className="mypage-title">
        <span className="cursor">▶</span>마이페이지
      </h1>

      {/* ---- 회원정보 ---- */}
      <section className="mypage-section" aria-labelledby="mypage-account-heading">
        <div className="mypage-section-title-row">
          <h2 className="mypage-section-title" id="mypage-account-heading">
            회원정보
          </h2>
          {editingNickname ? (
            <div className="mypage-title-actions">
              <button
                type="button"
                className="mypage-icon-btn mypage-icon-btn--save"
                onClick={saveNickname}
                disabled={savingNickname}
                aria-label="저장"
                title="저장"
              >
                {savingNickname ? <span className="spinner" aria-hidden="true" /> : '✓'}
              </button>
              <button
                type="button"
                className="mypage-icon-btn mypage-icon-btn--cancel"
                onClick={() => setEditingNickname(false)}
                disabled={savingNickname}
                aria-label="취소"
                title="취소"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="mypage-icon-btn mypage-icon-btn--add"
              onClick={startEditNickname}
              aria-label="회원정보 수정"
              title="회원정보 수정"
            >
              +
            </button>
          )}
        </div>
        <div className="mypage-account-card">
          <div className="mypage-account-body">
            <div className="mypage-account-photo-box">
              {editingNickname ? (
                <div className="mypage-avatar-option-col">
                  {PROFILE_ICON_OPTIONS.map(({ key, label, Icon }) => (
                    <button
                      key={key}
                      type="button"
                      className={`mypage-avatar-option${profileIconDraft === key ? ' is-active' : ''}`}
                      aria-pressed={profileIconDraft === key}
                      aria-label={label}
                      title={label}
                      onClick={() => setProfileIconDraft(profileIconDraft === key ? null : key)}
                    >
                      <Icon />
                    </button>
                  ))}
                </div>
              ) : (
                <span className="mypage-avatar-display" aria-hidden={!user.profile_icon}>
                  {(() => {
                    const selected = PROFILE_ICON_OPTIONS.find((opt) => opt.key === user.profile_icon);
                    return selected ? <selected.Icon /> : <span className="mypage-avatar-placeholder">?</span>;
                  })()}
                </span>
              )}
            </div>
            <div className="mypage-account-rows">
              <div className="mypage-account-row">
                <span className="mypage-account-label">닉네임</span>
                {editingNickname ? (
                  <input
                    type="text"
                    className="search-input login-input"
                    value={nicknameDraft}
                    onChange={(e) => setNicknameDraft(e.target.value)}
                    aria-label="닉네임 수정"
                    autoFocus
                  />
                ) : (
                  <span className="mypage-account-value">{user.nickname}</span>
                )}
              </div>
              <div className="mypage-account-row">
                <span className="mypage-account-label">나이</span>
                {editingNickname ? (
                  <input
                    type="number"
                    className="search-input login-input mypage-account-age-input"
                    value={ageDraft}
                    onChange={(e) => setAgeDraft(e.target.value)}
                    min={0}
                    max={120}
                    placeholder="선택 입력"
                    aria-label="나이 수정"
                  />
                ) : (
                  <span className="mypage-account-value">{user.age != null ? `${user.age}세` : '입력 안 함'}</span>
                )}
              </div>
              <div className="mypage-account-row">
                <span className="mypage-account-label">성별</span>
                {editingNickname ? (
                  <div className="mypage-chip-row">
                    {GENDER_OPTIONS.map((option) => (
                      <button
                        key={option}
                        type="button"
                        className={`mypage-chip${genderDraft === option ? ' is-active' : ''}`}
                        aria-pressed={genderDraft === option}
                        onClick={() => setGenderDraft(genderDraft === option ? null : option)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : (
                  <span className="mypage-account-value">{user.gender ?? '입력 안 함'}</span>
                )}
              </div>
              <div className="mypage-account-row">
                <span className="mypage-account-label">이메일</span>
                <span className="mypage-account-value">{user.email}</span>
              </div>
              <div className="mypage-account-row">
                <span className="mypage-account-label">가입일</span>
                <span className="mypage-account-value">{user.joined_at.slice(0, 10)}</span>
              </div>
            </div>
          </div>
        </div>

        {nicknameError && <p className="login-error">{nicknameError}</p>}
      </section>

      {/* ---- 저장한 결과 ---- */}
      <section className="mypage-section" aria-labelledby="mypage-saved-heading">
        <h2 className="mypage-section-title" id="mypage-saved-heading">
          저장한 결과
          {savedStatus === 'done' && <span className="mypage-section-count">{savedResults.length}개</span>}
        </h2>

        {savedStatus === 'loading' && (
          <p className="results-status">
            <span className="spinner" aria-hidden="true" /> 불러오는 중...
          </p>
        )}

        {savedStatus === 'error' && (
          <div className="error-banner" role="alert">
            {savedError}
          </div>
        )}

        {savedStatus === 'done' && savedError && (
          <p className="login-error" role="alert">
            {savedError}
          </p>
        )}

        {savedStatus === 'done' && savedResults.length === 0 && (
          <div className="results-empty">
            <p>아직 저장한 결과가 없어요.</p>
            <p className="results-empty-sub">전성분 결과 화면에서 저장하면 여기에 모여요.</p>
          </div>
        )}

        {savedStatus === 'done' && savedResults.length > 0 && (
          <div className="mypage-saved-grid">
            {savedResults.map((result) => (
              <div className="mypage-saved-card" key={result.id}>
                <button
                  type="button"
                  className="mypage-saved-card-remove"
                  onClick={() => unsaveResultCard(result.id)}
                  aria-label={`${result.productName} 저장 해제`}
                  title="저장 해제"
                >
                  ✕
                </button>
                <button type="button" className="mypage-saved-card-main" onClick={() => onSelectSavedResult(result)}>
                  {result.grade && (
                    <span className={`ing-badge ing-badge--${result.grade} mypage-saved-badge`}>
                      {GRADE_LABEL[result.grade]}
                    </span>
                  )}
                  <span className="mypage-saved-brand">{result.brand ?? '브랜드 정보 없음'}</span>
                  <span className="mypage-saved-name">{result.productName}</span>
                  {result.cautionCount != null && (
                    <span className="mypage-saved-meta">주의 성분 {result.cautionCount}개</span>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ---- 내 화장품 조합 ---- */}
      <section className="mypage-section" aria-labelledby="mypage-routine-heading">
        <h2 className="mypage-section-title" id="mypage-routine-heading">
          내 화장품 조합
        </h2>
        <p className="mypage-section-desc">
          쓰는 화장품을 등록하면 전성분을 합쳐서 수분·보습 밸런스와 내 피부 타입 기준 궁합을 분석해드려요.
        </p>
        {routineHistory.length > 0 && (
          <div className="mypage-saved-grid mypage-saved-grid--scroll">
            {routineHistory.map((entry) => (
              <div className="mypage-saved-card" key={entry.history_id}>
                <button
                  type="button"
                  className="mypage-saved-card-remove"
                  onClick={() => deleteRoutineHistoryCard(entry.history_id)}
                  aria-label="조합 기록 삭제"
                  title="삭제"
                >
                  ✕
                </button>
                <button
                  type="button"
                  className="mypage-saved-card-main"
                  onClick={() => onOpenRoutineHistory(entry)}
                >
                  <span className="mypage-saved-brand">
                    {new Date(entry.saved_at).toLocaleDateString('ko-KR', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </span>
                  <span className="mypage-saved-meta">{entry.product_count}개 제품</span>
                  {entry.products.length > 0 && (
                    <div className="mypage-chip-row">
                      {entry.products.map((p) => (
                        <span className="mypage-chip mypage-chip--tag" key={p.product_id}>
                          {p.product_name}
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
        <button type="button" className="mypage-ghost-btn" onClick={onOpenRoutine}>
          내 조합 확인하기
        </button>
      </section>

      {/* ---- 나의 피부 프로필 · 주의 성분 ---- */}
      <section className="mypage-section" aria-labelledby="mypage-skin-heading">
        <h2 className="mypage-section-title" id="mypage-skin-heading">
          나의 피부 프로필 · 주의 성분
        </h2>
        <p className="mypage-section-desc">
          등록해두면 다음 검색·스캔 결과에서 해당 성분이 나올 때 먼저 표시해줄 예정이에요.
        </p>

        {skinStatus === 'loading' && (
          <p className="results-status">
            <span className="spinner" aria-hidden="true" /> 불러오는 중...
          </p>
        )}

        {skinStatus === 'error' && (
          <div className="error-banner" role="alert">
            {skinLoadError}
          </div>
        )}

        {skinStatus === 'done' && skinProfile && (
          <div className="mypage-profile-card">
            <p className="mypage-profile-label">피부 타입 (복수 선택 가능)</p>
            <div className="mypage-chip-row">
              {SKIN_TYPE_OPTIONS.map((type) => (
                <button
                  key={type}
                  type="button"
                  className={`mypage-chip${skinProfile.skin_types.includes(type) ? ' is-active' : ''}`}
                  aria-pressed={skinProfile.skin_types.includes(type)}
                  onClick={() => toggleSkinType(type)}
                >
                  {type}
                </button>
              ))}
            </div>

            <p className="mypage-profile-label mypage-profile-label--spaced">주의하고 싶은 성분</p>
            <div className="mypage-chip-row">
              {skinProfile.watched_ingredients.map((ingredient) => (
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
            {skinSaveError && <p className="login-error">{skinSaveError}</p>}
            <p className="mypage-demo-note">변경사항은 자동으로 저장돼요.</p>
          </div>
        )}
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
            aria-checked={user.notify_alerts}
            onClick={toggleNotifyAlerts}
            disabled={notifySaving}
          >
            <span className={`mypage-toggle-box${user.notify_alerts ? ' is-on' : ''}`} aria-hidden="true">
              {notifySaving ? <span className="spinner" aria-hidden="true" /> : user.notify_alerts ? '✓' : ''}
            </span>
            <span className="mypage-toggle-text">
              <span className="mypage-toggle-title">주의 성분 알림 받기</span>
              <span className="mypage-toggle-sub">등록한 주의 성분이 검색·스캔 결과에 나오면 알려줘요.</span>
            </span>
          </button>
          {notifyError && <p className="login-error">{notifyError}</p>}

          <div className="mypage-settings-divider" role="separator" />

          <button type="button" className="mypage-settings-link" disabled title="준비 중">
            이용약관
          </button>
          <button type="button" className="mypage-settings-link" disabled title="준비 중">
            개인정보처리방침
          </button>
          <div className="mypage-settings-version">보고사라 v0.1.0 (데모)</div>

          <div className="mypage-settings-divider" role="separator" />

          <button
            type="button"
            className="mypage-ghost-btn mypage-ghost-btn--danger"
            onClick={() => {
              logout();
              onBack();
            }}
          >
            로그아웃
          </button>
          <button type="button" className="mypage-settings-link mypage-settings-link--danger" disabled title="준비 중">
            회원 탈퇴
          </button>
        </div>
      </section>
    </div>
  );
}
