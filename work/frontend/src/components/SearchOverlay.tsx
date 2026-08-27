import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

interface SearchOverlayProps {
  onClose: () => void;
}

/**
 * 히어로 왼쪽(SEARCH) 클릭 → 뜨는 전체화면 검색 오버레이 — 입력창 하나만 있는 심플한 화면.
 * 제출하면 /search?q=...로 이동하고 오버레이는 닫는다 (재검색은 검색 결과 페이지 자체 검색창에서).
 */
export function SearchOverlay({ onClose }: SearchOverlayProps) {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    onClose();
  };

  return (
    <div className="search-overlay">
      <button type="button" className="search-overlay__close" onClick={onClose} aria-label="닫기">
        ×
      </button>
      <form className="search-overlay__form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="search-overlay__input"
          placeholder="제품명을 입력하세요"
          autoComplete="off"
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <p className="search-overlay__hint">ENTER로 검색 · ESC로 닫기</p>
      </form>
    </div>
  );
}
