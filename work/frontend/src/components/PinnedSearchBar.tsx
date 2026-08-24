import { useState, type FormEvent } from 'react';

interface PinnedSearchBarProps {
  onSearch: (query: string) => void;
}

/**
 * 재검색용 바.
 *
 * [설계 메모] 검색 결과가 뜨면 큰 검색 오버레이(딤 배경 포함)는 닫고, 그 대신 이 얇은 바를
 * 노출한다 — 결과를 보면서도 큰 오버레이를 다시 띄우지 않고 바로 재검색할 수 있게 하기 위함
 * (돋보기 아이콘을 다시 눌러 큰 오버레이를 여는 것도 여전히 가능하다).
 * ResultsSection의 "검색 결과" 제목 줄 오른쪽에 나란히 배치된다 — 화면 맨 위에 고정하지 않고
 * 제목과 같은 높이, results-grid와 같은 칼럼 트랙 기준 오른쪽 두 칸에 정렬한다
 * (App.css의 .results-heading/.pinned-search 그리드 규칙 참고).
 */
export default function PinnedSearchBar({ onSearch }: PinnedSearchBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    onSearch(trimmed);
  };

  return (
    <form className="pinned-search" onSubmit={handleSubmit} role="search" aria-label="다시 검색">
      <input
        type="text"
        className="pinned-search-input"
        placeholder="다른 제품명으로 다시 검색"
        autoComplete="off"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button type="submit" className="pinned-search-btn">
        검색
      </button>
    </form>
  );
}
