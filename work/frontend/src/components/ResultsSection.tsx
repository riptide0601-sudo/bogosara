import { forwardRef } from 'react';
import type { Product } from '../data/mockProducts';
import ProductCard from './ProductCard';
import PinnedSearchBar from './PinnedSearchBar';

export type SearchStatus = 'idle' | 'loading' | 'done';

interface ResultsSectionProps {
  status: SearchStatus;
  query: string;
  results: Product[];
  onSelectProduct?: (product: Product) => void;
  onSearch: (query: string) => void;
}

/**
 * 검색 결과 섹션 — 페이지 이동 없이 검색 오버레이 아래쪽에 나타난다.
 * App.tsx가 검색 제출 시 이 섹션으로 smooth scroll 시킨다 (resultsRef 참고).
 * status: 'idle'(아직 검색 안 함, 렌더링 안 함) / 'loading'(스켈레톤) / 'done'(결과 또는 빈 상태)
 * onSelectProduct: 카드 클릭 시 성분 결과 화면(ResultView)으로 넘어가는 진입점 (ProductCard로 그대로 전달).
 * onSearch: 제목 줄 오른쪽에 나란히 놓인 재검색 바(PinnedSearchBar) 제출 핸들러 — 화면 맨 위에
 * 고정되던 이전 방식 대신, 이 제목 줄과 같은 높이·같은 칼럼 트랙에 우측 정렬로 배치한다
 * (App.css의 .results-heading/.pinned-search 그리드 정렬 참고).
 */
const ResultsSection = forwardRef<HTMLElement, ResultsSectionProps>(function ResultsSection(
  { status, query, results, onSelectProduct, onSearch },
  ref,
) {
  if (status === 'idle') return null;

  return (
    <section className="results-section" id="results-section" ref={ref} aria-live="polite">
      <div className="results-inner">
        <div className="results-heading">
          <h2 className="results-heading-title">
            <span className="cursor">▶</span>검색 결과
            {query && <span className="results-query">"{query}"</span>}
          </h2>
          <PinnedSearchBar onSearch={onSearch} />
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

        {status === 'done' && results.length === 0 && (
          <div className="results-empty">
            <p>검색 결과가 없어요.</p>
            <p className="results-empty-sub">다른 제품명으로 다시 검색해보세요.</p>
          </div>
        )}

        {status === 'done' && results.length > 0 && (
          <div className="results-grid">
            {results.map((product) => (
              <ProductCard key={product.id} product={product} onSelect={onSelectProduct} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
});

export default ResultsSection;
