import { useEffect, useState, type FormEvent } from 'react';
import { searchProducts } from '../api';
import { addToRoutine, getRoutineAnalysis, listRoutine, removeFromRoutine } from '../api/routine';
import { ApiError } from '../api/client';
import type { RoutineAnalysis, RoutineItemRead } from '../api/types';
import type { Product } from '../data/mockProducts';
import '../RoutineView.css';

interface RoutineViewProps {
  onBack: () => void;
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
 * 전환" 패턴이고, 뒤로가기는 항상 마이페이지로 돌아간다(App.tsx가 mypageOpen을 유지한 채
 * 이 화면만 닫는다).
 *
 * 등록 목록(items)과 분석 결과(analysis)는 서로 다른 API라 로딩/에러 상태를 따로 관리한다
 * — 목록 조회는 빨라도 분석은 여러 테이블을 조인하니 분석만 오래 걸리는 경우를 자연스럽게
 * 보여주기 위함. 제품을 추가/삭제하면 둘 다 다시 불러온다.
 */
export default function RoutineView({ onBack }: RoutineViewProps) {
  const [items, setItems] = useState<RoutineItemRead[]>([]);
  const [itemsStatus, setItemsStatus] = useState<FetchStatus>('loading');
  const [itemsError, setItemsError] = useState<string | null>(null);

  const [analysis, setAnalysis] = useState<RoutineAnalysis | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<FetchStatus>('loading');
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [searching, setSearching] = useState(false);
  const [addingId, setAddingId] = useState<string | null>(null);

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
        setSearching(false);
      })
      .catch((err) => {
        console.error('[보고사라][내 조합] 제품 검색 실패', err);
        setSearchResults([]);
        setSearching(false);
      });
  };

  const handleAdd = async (product: Product) => {
    setAddingId(product.id);
    try {
      await addToRoutine(product.id);
      loadItems();
      loadAnalysis();
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
    } catch (err) {
      setItems(prev);
      console.error('[보고사라][내 조합] 삭제 실패', err);
    }
  };

  const routineProductIds = new Set(items.map((i) => i.product_id));

  return (
    <div className="routine-view">
      <header className="result-topbar">
        <button type="button" className="result-back-btn" onClick={onBack}>
          <span className="cursor">◀</span>마이페이지로
        </button>
      </header>

      <h1 className="mypage-title">
        <span className="cursor">▶</span>내 화장품 조합
      </h1>
      <p className="mypage-section-desc">
        스킨/토너·세럼·크림 등 실제로 쓰는 제품을 등록하면, 전성분을 합쳐서 수분·보습 밸런스와
        내 피부 타입 기준 궁합을 분석해드려요.
      </p>

      {/* ---- 분석 결과 ---- */}
      <section className="mypage-section" aria-labelledby="routine-analysis-heading">
        <h2 className="mypage-section-title" id="routine-analysis-heading">
          조합 분석
        </h2>

        {analysisStatus === 'loading' && (
          <p className="results-status">
            <span className="spinner" aria-hidden="true" /> 분석하는 중...
          </p>
        )}
        {analysisStatus === 'error' && (
          <div className="error-banner" role="alert">
            {analysisError}
          </div>
        )}
        {analysisStatus === 'done' && analysis && (
          <div className="mypage-profile-card">
            <p className="result-headline">“{analysis.headline}”</p>

            {analysis.overall_description && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>조합 설명
                </h3>
                <p className="result-explain">{analysis.overall_description}</p>
              </div>
            )}

            {itemsStatus === 'done' && items.length > 0 && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>제품별 살펴보기
                </h3>
                <div className="routine-product-notes">
                  {items.map((item) => (
                    <div className="routine-product-note" key={item.product_id}>
                      <p className="routine-product-note-name">{item.product_name}</p>
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

            {(analysis.relations ?? []).length > 0 && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>성분 조합
                </h3>
                <ul className="result-caution-list">
                  {analysis.relations.map((rel, i) => (
                    <li className="result-caution-item" key={i}>
                      <p className="result-caution-name">
                        {rel.relation_type === '악화' && '⚠ '}
                        {rel.ingredient_a} + {rel.ingredient_b} · {rel.relation_type}
                      </p>
                      {rel.message && <p className="result-caution-reason">{rel.message}</p>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.product_count > 0 && (
              <div className="result-section">
                <h3 className="result-section-title">
                  <span className="cursor">▶</span>수분 · 보습 밸런스
                </h3>
                <p className="result-explain">{analysis.hydration_note}</p>
              </div>
            )}

            {analysis.skin_type_notes.map((note) => (
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
                          {ing.name_kr} · 잘 맞아요
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
                        <p className="result-caution-name routine-ingredient-trigger" tabIndex={0}>
                          ⚠ {ing.name_kr} · 주의
                          {ing.reason && (
                            <span className="routine-ingredient-tooltip" role="tooltip">
                              {ing.reason}
                            </span>
                          )}
                        </p>
                        {ing.description && <p className="result-caution-reason">{ing.description}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}

            {analysis.product_count > 0 && analysis.skin_type_notes.length === 0 && (
              <div className="result-section">
                <p className="result-explain">
                  마이페이지에서 피부 타입을 등록하면 내 피부 기준 궁합도 함께 보여드려요.
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ---- 등록한 화장품 ---- */}
      <section className="mypage-section" aria-labelledby="routine-items-heading">
        <h2 className="mypage-section-title" id="routine-items-heading">
          등록한 화장품
          {itemsStatus === 'done' && <span className="mypage-section-count">{items.length}개</span>}
        </h2>

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
            autoComplete="off"
          />
          <button type="submit" className="mypage-ghost-btn" disabled={searching}>
            {searching ? <span className="spinner" aria-hidden="true" /> : '검색'}
          </button>
        </form>

        {searchResults.length > 0 && (
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
    </div>
  );
}
