import { useState, type FormEvent } from 'react';
import Overlay from './Overlay';

interface SearchOverlayProps {
  open: boolean;
  onClose: () => void;
  onSearch: (query: string) => void;
}

/**
 * 돋보기 클릭 → 뜨는 검색 오버레이 (첫 검색 진입점).
 *
 * [설계 메모] 검색을 제출하면 이 큰 오버레이는 닫고 결과 섹션으로 스크롤한다.
 * 이후 재검색은 상단에 고정되는 얇은 PinnedSearchBar로 처리한다 (App.tsx 참고).
 */
export default function SearchOverlay({ open, onClose, onSearch }: SearchOverlayProps) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = query.trim();

    if (!trimmed) {
      setStatus('검색어를 입력해주세요.');
      return;
    }

    setStatus('');
    onSearch(trimmed);
    onClose(); // 결과가 뜨는 즉시 큰 오버레이는 닫는다 (재검색은 상단 고정 바에서)
  };

  return (
    <Overlay id="overlay-search" titleId="search-title" title="성분 검색" open={open} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="search-row">
          <input
            type="text"
            className="search-input"
            placeholder="제품명을 입력하세요 (예: OO 선크림)"
            autoComplete="off"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn-primary">
            검색
          </button>
        </div>
        <p className="search-status" role="status">
          {status}
        </p>
      </form>
    </Overlay>
  );
}
