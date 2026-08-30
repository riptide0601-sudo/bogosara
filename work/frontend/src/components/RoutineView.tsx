import { useEffect, useState, type FormEvent } from 'react';
import { searchProducts } from '../api';
import {
  addToRoutine,
  clearRoutine,
  getRoutineAnalysis,
  listRoutine,
  removeFromRoutine,
  saveRoutineHistory,
} from '../api/routine';
import { ApiError } from '../api/client';
import type { RoutineAnalysis, RoutineHistoryProduct, RoutineHistoryRead, RoutineItemRead } from '../api/types';
import type { Product } from '../data/mockProducts';
import '../RoutineView.css';

function formatSavedAt(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
}

/** ingredient_skin_score.caution 원문은 "EU 화장품규정 지정 향료 알레르겐 26종 중 하나.
 * 산화 시 알레르기 유발력 증가. 피부타입과 무관하게 개인 감작 위험 존재"처럼 문장 여러 개가
 * 이어질 수 있어서, "주의" 카드엔 핵심만 보이도록 첫 문장만 잘라서 보여준다. */
function shortenReason(reason: string): string {
  const firstSentence = reason.split('.')[0].trim();
  return firstSentence || reason;
}

interface RoutineViewProps {
  onBack: () => void;
  onSelectProduct: (productId: string) => void;
  /** 마이페이지/조합 기록의 저장된 카드를 눌러 들어온 경우 — 그 시점 조합(제품 목록)과
   * 그걸 다시 분석한 결과. 있으면 "조합 분석" 섹션이 지금 등록된 조합 대신 이걸 먼저
   * 보여준다. analysis는 히스토리 엔트리를 클릭한 직후 비동기로 불러오므로 잠깐 null일
   * 수 있다(로딩 중) — entry는 라우터 state로 바로 들어와 있어 항상 값이 있다. */
  historyEntry?: RoutineHistoryRead | null;
  historyAnalysis?: RoutineAnalysis | null;
}

type FetchStatus = 'loading' | 'done' | 'error';

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return '네트워크 상태를 확인하고 다시 시도해주세요.';
}

/**
 * 마이페이지 "내 화장품 조합" — 실제로 쓰는 화장품(스킨/토너·세럼·크림 등)을 등록하면
 * app/routine_analysis.py가 전성분을 합쳐서 수분/보습 밸런스와 내 피부 타입(마이페이지에
 * 등록한 skin_types) 기준 위험/궁합 성분을 판정해준다. ResultView와 같은 "페이지 전체
 * 전환" 패턴이고, 상단 "뒤로가기"는 브라우저 히스토리로 돌아간다 — 랜딩의 바로가기·마이페이지의
 * "내 조합 확인하기" 어느 쪽에서 들어와도 원래 있던 곳으로 자연스럽게 돌아간다.
 *
 * 등록 목록(items)과 분석 결과(analysis)는 서로 다른 API라 로딩/에러 상태를 따로 관리한다
 * — 목록 조회는 빨라도 분석은 여러 테이블을 조인하니 분석만 오래 걸리는 경우를 자연스럽게
 * 보여주기 위함. 제품을 추가/삭제하면 둘 다 다시 불러온다.
 */
export default function RoutineView({
  onBack,
  onSelectProduct,
  historyEntry,
  historyAnalysis,
}: RoutineViewProps) {
  const [showingHistory, setShowingHistory] = useState(!!historyEntry);
  const [showBalanceIngredients, setShowBalanceIngredients] = useState(false);
  const [items, setItems] = useState<RoutineItemRead[]>([]);
  const [itemsStatus, setItemsStatus] = useState<FetchStatus>('loading');
  const [itemsError, setItemsError] = useState<string | null>(null);

  const [analysis, setAnalysis] = useState<RoutineAnalysis | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<FetchStatus>('loading');
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  // 검색 결과는 "추가" 후 목록만 접어두고(searchResults는 그대로 둔다) — 검색창에 단어가
  // 남아있는 채로 다시 포커스하면 방금 그 결과를 다시 펼쳐서 보여준다.
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [searching, setSearching] = useState(false);
  const [addingId, setAddingId] = useState<string | null>(null);
  const [clearingItems, setClearingItems] = useState(false);

  const [savingHistory, setSavingHistory] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const loadItems = () => {
    setItemsStatus('loading');
    listRoutine()
      .then((results) => {
        setItems(results);
        setItemsStatus('done');
      })
      .catch((err) => {
        setItemsError(errorMessage(err));
        setItemsStatus('error');
      });
  };

  const loadAnalysis = () => {
    setAnalysisStatus('loading');
    getRoutineAnalysis()
      .then((result) => {
        setAnalysis(result);
        setAnalysisStatus('done');
      })
      .catch((err) => {
        setAnalysisError(errorMessage(err));
        setAnalysisStatus('error');
      });
  };

  useEffect(() => {
    loadItems();
    loadAnalysis();
  }, []);

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    setSearching(true);
    searchProducts(trimmed)
      .then((results) => {
        setSearchResults(results);
        setShowSearchResults(true);
        setSearching(false);
      })
      .catch((err) => {
        console.error('[보고사라][내 조합] 제품 검색 실패', err);
        setSearchResults([]);
        setSearching(false);
      });
  };

  const handleSearchInputFocus = () => {
    if (query.trim() && searchResults.length > 0) setShowSearchResults(true);
  };

  const handleAdd = async (product: Product) => {
    setAddingId(product.id);
    try {
      await addToRoutine(product.id);
      loadItems();
      loadAnalysis();
      // 추가하고 나면 검색 결과 목록은 접어둔다 — 검색창에 단어가 남아있는 채로 다시
      // 포커스하면(handleSearchInputFocus) 곧바로 다시 펼쳐진다.
      setShowSearchResults(false);
      // 조합 구성이 바뀌었으니 이전 "저장됨" 상태는 풀어서 다시 저장할 수 있게 한다.
      setSaveSuccess(false);
    } catch (err) {
      console.error('[보고사라][내 조합] 추가 실패', err);
    } finally {
      setAddingId(null);
    }
  };

  const handleRemove = async (productId: string) => {
    const prev = items;
    setItems((list) => list.filter((i) => i.product_id !== productId));
    try {
      await removeFromRoutine(productId);
      loadAnalysis();
      setSaveSuccess(false);
    } catch (err) {
      setItems(prev);
      console.error('[보고사라][내 조합] 삭제 실패', err);
    }
  };

  const handleClearItems = async () => {
    if (clearingItems || items.length === 0) return;
    const prev = items;
    setClearingItems(true);
    setItems([]);
    try {
      await clearRoutine(prev.map((i) => i.product_id));
      loadAnalysis();
      setSaveSuccess(false);
    } catch (err) {
      setItems(prev);
      console.error('[보고사라][내 조합] 초기화 실패', err);
    } finally {
      setClearingItems(false);
    }
  };

  const handleSaveHistory = async () => {
    setSavingHistory(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await saveRoutineHistory();
      setSaveSuccess(true);
    } catch (err) {
      setSaveError(errorMessage(err));
    } finally {
      setSavingHistory(false);
    }
  };

  const routineProductIds = new Set(items.map((i) => i.product_id));
  const displayAnalysis = showingHistory ? historyAnalysis ?? null : analysis;

  return (
    <div className="routine-view">
      <header className="result-topbar">
        <button type="button" className="result-back-btn" onClick={onBack}>
          <span className="cursor">◀</span>뒤로가기
        </button>
      </header>

      <h1 className="mypage-title">
        <span className="cursor">▶</span>내 화장품 조합
      </h1>
      <p className="mypage-section-desc">
        스킨/토너·세럼·크림 등 실제로 쓰는 제품을 등록하면, 전성분을 합쳐서 수분·보습 밸런스와
        내 피부 타입 기준 궁합을 분석해드려요.
      </p>

      {/* ---- 등록한 화장품 ---- */}
      <section className="mypage-section" aria-labelledby="routine-items-heading">
        <div className="mypage-section-title-row">
          <h2 className="mypage-section-title" id="routine-items-heading">
            등록한 화장품
            {itemsStatus === 'done' && <span className="mypage-section-count">{items.length}개</span>}
          </h2>
          {itemsStatus === 'done' && items.length > 0 && (
            <button
              type="button"
              className="mypage-icon-btn routine-clear-btn"
              onClick={handleClearItems}
              disabled={clearingItems}
              aria-label="등록한 화장품 초기화"
              title="초기화"
            >
              {clearingItems ? <span className="spinner" aria-hidden="true" /> : '↺'}
            </button>
          )}
        </div>

        {itemsStatus === 'loading' && (
          <p className="results-status">
            <span className="spinner" aria-hidden="true" /> 불러오는 중...
          </p>
        )}
        {itemsStatus === 'error' && (
          <div className="error-banner" role="alert">
            {itemsError}
          </div>
        )}
        {itemsStatus === 'done' && items.length === 0 && (
          <div className="results-empty">
            <p>아직 등록한 화장품이 없어요.</p>
            <p className="results-empty-sub">아래에서 검색해서 추가해보세요.</p>
          </div>
        )}
        {itemsStatus === 'done' && items.length > 0 && (
          <ul className="routine-item-list">
            {items.map((item) => (
              <li className="routine-item-row" key={item.product_id}>
                <span className="routine-item-category">{item.category ?? '기타'}</span>
                <span className="routine-item-info">
                  <span className="photo-reco-brand">{item.brand ?? '브랜드 정보 없음'}</span>
                  <span className="routine-item-name">{item.product_name}</span>
                </span>
                <button
                  type="button"
                  className="mypage-ghost-btn"
                  onClick={() => onSelectProduct(item.product_id)}
                >
                  성분 보기
                </button>
                <button
                  type="button"
                  className="mypage-chip-remove"
                  onClick={() => handleRemove(item.product_id)}
                  aria-label={`${item.product_name} 삭제`}
                  title="삭제"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}

        <form className="routine-search" onSubmit={handleSearch} role="search" aria-label="화장품 검색해서 추가">
          <input
            type="text"
            className="search-input routine-search-input"
            placeholder="제품명으로 검색해서 추가"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={handleSearchInputFocus}
            autoComplete="off"
          />
          <button type="submit" className="mypage-ghost-btn" disabled={searching}>
            {searching ? <span className="spinner" aria-hidden="true" /> : '검색'}
          </button>
        </form>

        {showSearchResults && searchResults.length > 0 && (
          <ul className="routine-item-list routine-search-results">
            {searchResults.map((product) => {
              const already = routineProductIds.has(product.id);
              return (
                <li className="routine-item-row" key={product.id}>
                  <span className="routine-item-info">
                    <span className="photo-reco-brand">{product.brand}</span>
                    <span className="routine-item-name">{product.name}</span>
                  </span>
                  <button
                    type="button"
                    className="mypage-ghost-btn"
                    onClick={() => handleAdd(product)}
                    disabled={already || addingId === product.id}
                  >
                    {already ? (
                      '등록됨'
                    ) : addingId === product.id ? (
                      <span className="spinner" aria-hidden="true" />
                    ) : (
                      '추가'
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* ---- 분석 결과 ---- */}
      <section className="mypage-section" aria-labelledby="routine-analysis-heading">
        <h2 className="mypage-section-title" id="routine-analysis-heading">
          {showingHistory && historyEntry ? `조합 분석 · 기록 (${formatSavedAt(historyEntry.saved_at)})` : '조합 분석'}
        </h2>
        {showingHistory && (
          <button
            type="button"
            className="mypage-ghost-btn routine-history-back-btn"
            onClick={() => setShowingHistory(false)}
          >
            ← 지금 조합 분석 보기
          </button>
        )}

        {showingHistory && !displayAnalysis && (
          <p className="results-status">
            <span className="spinner" aria-hidden="true" /> 불러오는 중...
          </p>
        )}
        {!showingHistory && analysisStatus === 'loading' && (
          <p className="results-status">
            <span className="spinner" aria-hidden="true" /> 분석하는 중...
          </p>
        )}
        {!showingHistory && analysisStatus === 'error' && (
          <div className="error-banner" role="alert">
            {analysisError}
          </div>
        )}
        {displayAnalysis && displayAnalysis.product_count === 0 && (
          <div className="results-empty">
            <p>{displayAnalysis.headline}</p>
          </div>
        )}
        {displayAnalysis && displayAnalysis.product_count > 0 && (
          <div className="mypage-profile-card">
            <p className="result-headline">“{displayAnalysis.headline}”</p>

            {displayAnalysis.overall_description && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>조합 설명
                </h3>
                <p className="result-explain">{displayAnalysis.overall_description}</p>
              </div>
            )}

            {!showingHistory && itemsStatus === 'done' && items.length > 0 && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>제품별 살펴보기
                </h3>
                <div className="routine-product-notes">
                  {items.map((item) => (
                    <div className="routine-product-note" key={item.product_id}>
                      <button
                        type="button"
                        className="routine-product-note-name"
                        onClick={() => onSelectProduct(item.product_id)}
                      >
                        {item.product_name} <span className="routine-product-note-arrow">→</span>
                      </button>
                      {item.description && <p className="result-explain">{item.description}</p>}
                      {(item.key_ingredients ?? []).length > 0 && (
                        <div className="mypage-chip-row">
                          {item.key_ingredients.map((name) => (
                            <span className="mypage-chip mypage-chip--tag" key={name}>
                              {name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {showingHistory && historyEntry && historyEntry.products.length > 0 && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>제품별 살펴보기
                </h3>
                <div className="routine-product-notes">
                  {historyEntry.products.map((p: RoutineHistoryProduct) => (
                    <div className="routine-product-note" key={p.product_id}>
                      <button
                        type="button"
                        className="routine-product-note-name"
                        onClick={() => onSelectProduct(p.product_id)}
                      >
                        {p.product_name} <span className="routine-product-note-arrow">→</span>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(displayAnalysis.relations ?? []).length > 0 && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>성분 조합
                </h3>
                <ul className="result-caution-list">
                  {displayAnalysis.relations.map((rel, i) => (
                    <li className="result-caution-item" key={i}>
                      <p className="result-caution-name">
                        {rel.ingredient_a} + {rel.ingredient_b} ·{' '}
                        <span
                          className={`routine-relation-type routine-relation-type--${
                            rel.relation_type === '시너지' ? 'good' : 'risk'
                          }`}
                        >
                          {rel.relation_type === '시너지' ? '↑' : '↓'} {rel.relation_type}
                        </span>
                      </p>
                      {rel.message && <p className="result-caution-reason">{rel.message}</p>}
                      {rel.relation_type === '악화' &&
                        (rel.alternatives_a.length > 0 || rel.alternatives_b.length > 0) && (
                          <div className="routine-relation-alternatives">
                            {rel.product_a && rel.alternatives_a.length > 0 && (
                              <p className="routine-relation-alt-row">
                                <span className="routine-relation-alt-label">
                                  {rel.product_a.product_name} 대신 이런 제품은 어때요?
                                </span>
                                {rel.alternatives_a.map((alt) => (
                                  <button
                                    key={alt.product_id}
                                    type="button"
                                    className="routine-relation-alt-chip"
                                    onClick={() => onSelectProduct(alt.product_id)}
                                  >
                                    {alt.product_name}
                                  </button>
                                ))}
                              </p>
                            )}
                            {rel.product_b && rel.alternatives_b.length > 0 && (
                              <p className="routine-relation-alt-row">
                                <span className="routine-relation-alt-label">
                                  {rel.product_b.product_name} 대신 이런 제품은 어때요?
                                </span>
                                {rel.alternatives_b.map((alt) => (
                                  <button
                                    key={alt.product_id}
                                    type="button"
                                    className="routine-relation-alt-chip"
                                    onClick={() => onSelectProduct(alt.product_id)}
                                  >
                                    {alt.product_name}
                                  </button>
                                ))}
                              </p>
                            )}
                          </div>
                        )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {displayAnalysis.product_count > 0 && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>수분 · 보습 밸런스
                </h3>
                {(displayAnalysis.hydration_ingredients.length > 0 || displayAnalysis.occlusion_ingredients.length > 0) && (
                  <>
                    <button
                      type="button"
                      className="routine-balance-toggle"
                      onClick={() => setShowBalanceIngredients((v) => !v)}
                      aria-expanded={showBalanceIngredients}
                    >
                      수분·보습에 해당하는 성분이 뭔가요?
                    </button>
                    {showBalanceIngredients && (
                      <>
                        {displayAnalysis.hydration_ingredients.length > 0 && (
                          <p className="routine-balance-ingredients">
                            <span className="routine-balance-ingredients-label">수분:</span>{' '}
                            {displayAnalysis.hydration_ingredients.join(', ')}
                          </p>
                        )}
                        {displayAnalysis.occlusion_ingredients.length > 0 && (
                          <p className="routine-balance-ingredients">
                            <span className="routine-balance-ingredients-label">보습:</span>{' '}
                            {displayAnalysis.occlusion_ingredients.join(', ')}
                          </p>
                        )}
                      </>
                    )}
                  </>
                )}
                {(displayAnalysis.hydration_count > 0 || displayAnalysis.occlusion_count > 0) && (
                  <div className="skin-type-bar-list routine-balance-bars">
                    <div className="skin-type-bar-row">
                      <div className="skin-type-bar-items">
                        <div className="skin-type-bar-item">
                          <div className="skin-type-bar-track">
                            <div
                              className="skin-type-bar-fill skin-type-bar-fill--good"
                              style={{
                                width: `${(displayAnalysis.hydration_count / Math.max(1, displayAnalysis.hydration_count + displayAnalysis.occlusion_count)) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="skin-type-bar-item-label skin-type-bar-item-label--wide">
                            수분 {displayAnalysis.hydration_count}/
                            {displayAnalysis.hydration_count + displayAnalysis.occlusion_count}
                          </span>
                        </div>
                        <div className="skin-type-bar-item">
                          <div className="skin-type-bar-track">
                            <div
                              className="skin-type-bar-fill skin-type-bar-fill--moisture"
                              style={{
                                width: `${(displayAnalysis.occlusion_count / Math.max(1, displayAnalysis.hydration_count + displayAnalysis.occlusion_count)) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="skin-type-bar-item-label skin-type-bar-item-label--wide">
                            보습 {displayAnalysis.occlusion_count}/
                            {displayAnalysis.hydration_count + displayAnalysis.occlusion_count}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {displayAnalysis.skin_type_notes.map((note) => (
              <div className="result-section" key={note.skin_type}>
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>
                  {note.skin_type} 피부 기준
                </h3>
                {note.good_ingredients.length === 0 && note.risk_ingredients.length === 0 && (
                  <p className="result-explain">현재 등록된 조합에서 특별히 확인된 성분은 없어요.</p>
                )}
                {(note.good_ingredients.length > 0 || note.risk_ingredients.length > 0) && (
                  <ul className="result-caution-list">
                    {note.good_ingredients.map((ing) => (
                      <li className="result-caution-item" key={`good-${ing.ingredient_id}`}>
                        <p className="result-caution-name routine-ingredient-trigger" tabIndex={0}>
                          {ing.name_kr} · <span className="routine-ingredient-status routine-ingredient-status--good">잘 맞아요</span>
                          {ing.reason && (
                            <span className="routine-ingredient-tooltip" role="tooltip">
                              {ing.reason}
                            </span>
                          )}
                        </p>
                        {ing.description && <p className="result-caution-reason">{ing.description}</p>}
                      </li>
                    ))}
                    {note.risk_ingredients.map((ing) => (
                      <li className="result-caution-item" key={`risk-${ing.ingredient_id}`}>
                        <p className="result-caution-name">
                          ⚠ {ing.name_kr} · <span className="routine-ingredient-status routine-ingredient-status--risk">주의</span>
                        </p>
                        {/* ing.description(ingredient.summary)은 "이 원료는 다음의 구조를 갖는
                            OO이다" 같은 화학 구조 정의문이라 "주의" 카드엔 안 어울린다 — 왜
                            주의해야 하는지 실제 근거인 ing.reason(ingredient_skin_score.caution)을
                            첫 문장만 잘라서 보여준다. */}
                        {ing.reason && <p className="result-caution-reason">{shortenReason(ing.reason)}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}

            {displayAnalysis.product_count > 0 && displayAnalysis.skin_type_notes.length === 0 && (
              <div className="result-section">
                <p className="result-explain">
                  마이페이지에서 피부 타입을 등록하면 내 피부 기준 궁합도 함께 보여드려요.
                </p>
              </div>
            )}
          </div>
        )}

        {!showingHistory && analysisStatus === 'done' && analysis && analysis.product_count > 0 && (
          <div className="routine-save-history">
            <button
              type="button"
              className="mypage-ghost-btn routine-save-btn"
              onClick={handleSaveHistory}
              disabled={savingHistory || saveSuccess}
            >
              이 조합 저장하기
              {savingHistory && <span className="spinner routine-save-btn-icon" aria-hidden="true" />}
              {!savingHistory && saveSuccess && !saveError && (
                <span className="routine-save-btn-icon routine-save-btn-icon--check" aria-hidden="true">
                  ✓
                </span>
              )}
            </button>
            {saveError && (
              <p className="results-empty-sub" role="alert">
                {saveError}
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
