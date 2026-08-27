import { useEffect, useState, type FormEvent } from 'react';
import type { Product } from '../data/mockProducts';
import type { SearchStatus } from './ResultsSection';
import '../SearchResultsView.css';

const PAGE_SIZE = 8;

interface SearchResultsViewProps {
  status: SearchStatus;
  query: string;
  results: Product[];
  onSelectProduct: (product: Product) => void;
  onSearch: (query: string) => void;
  onBack: () => void;
  onOpenMyPage: () => void;
  onOpenScan: () => void;
}

/**
 * 검색 결과 화면 — bogo1(SearchResultsPage.tsx) 디자인 이식. 기존 ResultsSection(랜딩
 * 페이지 아래쪽에 이어 붙던 인라인 섹션)을 대체하는 전체화면 페이지다.
 * 실제 데이터(product.image_url)를 쓰고, 사진이 없으면 bogo1처럼 라임색 박스를 그대로 둔다
 * (bogo1은 목업 사진 하나를 모든 카드에 재사용했지만, 우리는 실제 사진 유무로 갈린다).
 */
export default function SearchResultsView({
  status,
  query,
  results,
  onSelectProduct,
  onSearch,
  onBack,
  onOpenMyPage,
  onOpenScan,
}: SearchResultsViewProps) {
  const [page, setPage] = useState(1);
  const [rebox, setRebox] = useState('');

  useEffect(() => {
    setPage(1);
  }, [query, results]);

  const totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  const pageResults = results.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleResearch = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = rebox.trim();
    if (!trimmed) return;
    onSearch(trimmed);
    setRebox('');
  };

  return (
    <div className="sres-page">
      <header className="sres-topbar">
        <button type="button" className="sres-topbar-back" onClick={onBack}>
          ← BOGOSARA
        </button>
        <button type="button" className="sres-topbar-mypage" onClick={onOpenMyPage}>
          마이페이지
        </button>
      </header>

      <div className="sres-body">
        <div className="sres-meta-row">
          <p className="sres-meta">
            {query ? (
              <>
                <strong>"{query}"</strong> 검색결과 {results.length}개
              </>
            ) : (
              '검색 결과'
            )}
          </p>
          <form className="sres-searchbar" onSubmit={handleResearch}>
            <input
              type="text"
              className="sres-searchbar-input"
              value={rebox}
              onChange={(e) => setRebox(e.target.value)}
              placeholder="다시 검색하기"
              autoComplete="off"
            />
            <button type="submit" className="sres-searchbar-submit" aria-label="검색">
              ⌕
            </button>
          </form>
        </div>

        {status === 'loading' && <p className="sres-status">제품을 찾는 중…</p>}

        {status === 'error' && <p className="sres-status">검색 중 문제가 생겼어요. 다시 시도해주세요.</p>}

        {status === 'done' && results.length === 0 && (
          <div className="sres-empty">
            <h2 className="sres-empty-title">검색 결과가 없어요</h2>
            <p className="sres-empty-desc">다른 제품명으로 다시 검색하거나, 전성분표를 스캔해보세요.</p>
            <button type="button" className="sres-empty-cta" onClick={onOpenScan}>
              스캔하기 →
            </button>
          </div>
        )}

        {status === 'done' && results.length > 0 && (
          <>
            <ul className="sres-grid">
              {pageResults.map((product) => (
                <li key={product.id}>
                  <button
                    type="button"
                    className="sres-card"
                    onClick={() => onSelectProduct(product)}
                  >
                    <span className="sres-card-link">
                      {product.image_url ? (
                        <img className="sres-card-thumb" src={product.image_url} alt="" />
                      ) : (
                        <span className="sres-card-thumb" aria-hidden="true" />
                      )}
                      <span className="sres-card-name">{product.name}</span>
                      <span className="sres-card-brand">{product.brand}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>

            {totalPages > 1 && (
              <nav className="sres-pagination" aria-label="페이지">
                {Array.from({ length: totalPages }).map((_, i) => {
                  const n = i + 1;
                  return (
                    <button
                      key={n}
                      type="button"
                      className="sres-pagination-btn"
                      aria-current={n === page ? 'page' : undefined}
                      onClick={() => setPage(n)}
                    >
                      {n}
                    </button>
                  );
                })}
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  );
}
