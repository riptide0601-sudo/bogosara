import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { searchProducts } from '../api';
import type { Product } from '../data/mockProducts';
import ProductCard from '../components/ProductCard';
import BackgroundSparkles from '../components/BackgroundSparkles';
import SiteSidebar from '../components/SiteSidebar';
// 페이지네이션 버튼(.mypage-chip)만 빌려 쓴다 — 별도 CSS 새로 안 만들고 기존 픽셀 스타일 재사용.
import '../MyPageView.css';

const PAGE_SIZE = 8;

type Status = 'idle' | 'loading' | 'done' | 'error';

/**
 * 전용 검색 결과 페이지(/search?q=...) — 예전엔 랜딩 페이지 안에 인라인으로만 나오던 검색
 * 결과를, URL로 공유·새로고침 유지가 되는 독립 페이지로 옮겼다. 시각 스타일은 랜딩/결과
 * 화면과 같은 픽셀게임 디자인(App.css)을 그대로 쓴다 — ResultsSection이 쓰던
 * .results-section/.results-grid/ProductCard/PinnedSearchBar 클래스·컴포넌트를 그대로
 * 재사용해서, 인라인이던 걸 페이지 레벨로만 옮겼을 뿐 새 디자인을 들여오지 않았다.
 */
export default function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') ?? '';
  const inputRef = useRef<HTMLInputElement>(null);
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<Product[]>([]);
  const [status, setStatus] = useState<Status>('idle');

  useEffect(() => {
    if (inputRef.current) inputRef.current.value = query;
    setPage(1);

    if (!query) {
      setResults([]);
      setStatus('idle');
      return;
    }

    let cancelled = false;
    setStatus('loading');

    searchProducts(query)
      .then((products) => {
        if (cancelled) return;
        setResults(products);
        setStatus('done');
      })
      .catch((err) => {
        console.error('[보고사라][검색] API 호출 실패', err);
        if (!cancelled) setStatus('error');
      });

    return () => {
      cancelled = true;
    };
  }, [query]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = inputRef.current?.value.trim();
    if (!q) return;
    navigate(`/search?q=${encodeURIComponent(q)}`);
  };

  const handleSelectProduct = (product: Product) => {
    navigate(`/product/${product.id}`);
  };

  const totalPages = Math.ceil(results.length / PAGE_SIZE);
  const pageResults = results.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <>
      <BackgroundSparkles />
      <SiteSidebar />
      <section className="results-section" aria-live="polite">
        <div className="results-inner">
          <header className="result-topbar">
            <Link className="result-back-btn" to="/">
              <span className="cursor">◀</span>홈으로
            </Link>
          </header>

          <div className="results-heading">
            <h2 className="results-heading-title">
              <span className="cursor">▶</span>검색 결과
              {query && <span className="results-query">"{query}"</span>}
            </h2>
            <form className="pinned-search" onSubmit={handleSubmit} role="search" aria-label="다시 검색">
              <input
                ref={inputRef}
                type="text"
                className="pinned-search-input"
                placeholder="다른 제품명으로 다시 검색"
                autoComplete="off"
                defaultValue={query}
              />
              <button type="submit" className="pinned-search-btn">
                검색
              </button>
            </form>
          </div>

          {status === 'loading' && (
            <>
              <p className="results-status">제품을 찾는 중</p>
              <div className="results-grid" aria-hidden="true">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div className="skeleton-card" key={i} />
                ))}
              </div>
            </>
          )}

          {status === 'error' && (
            <div className="results-empty" role="alert">
              <p>검색 중 문제가 생겼어요.</p>
              <p className="results-empty-sub">네트워크 상태를 확인하고 다시 검색해보세요.</p>
            </div>
          )}

          {status === 'done' && results.length === 0 && (
            <div className="results-empty">
              <p>'{query}'와 일치하는 제품이 없어요.</p>
              <p className="results-empty-sub">
                등록된 제품이 아니라면, 전성분표를 촬영해서 바로 확인할 수 있어요.
              </p>
            </div>
          )}

          {status === 'done' && results.length > 0 && (
            <>
              <div className="results-grid">
                {pageResults.map((product) => (
                  <ProductCard key={product.id} product={product} onSelect={handleSelectProduct} />
                ))}
              </div>

              {totalPages > 1 && (
                <nav className="mypage-chip-row results-pagination" aria-label="페이지">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
                    <button
                      key={n}
                      type="button"
                      className={`mypage-chip${n === page ? ' is-active' : ''}`}
                      aria-current={n === page ? 'page' : undefined}
                      onClick={() => setPage(n)}
                    >
                      {n}
                    </button>
                  ))}
                </nav>
              )}
            </>
          )}
        </div>
      </section>
    </>
  );
}
