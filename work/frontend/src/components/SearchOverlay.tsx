import { useEffect, useRef, useState, type FormEvent } from 'react';
import '../SearchResultsView.css';

interface SearchOverlayProps {
  open: boolean;
  onClose: () => void;
  onSearch: (query: string) => void;
}

/**
 * 돋보기 클릭 → 뜨는 검색 오버레이 (첫 검색 진입점) — bogo1 디자인 이식.
 * 기존 픽셀 스타일 모달(Overlay.tsx 박스) 대신, 화면 전체를 덮는 크림색 배경에 큼직한
 * 밑줄 입력창 하나만 가운데 두는 전체화면 오버레이로 바꿨다.
 *
 * [설계 메모] 검색을 제출하면 이 오버레이는 닫고 결과 화면으로 넘어간다(App.tsx의
 * SearchResultsView) — 이후 재검색은 그 화면 안의 검색바로 처리한다.
 */
export default function SearchOverlay({ open, onClose, onSearch }: SearchOverlayProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    onSearch(trimmed);
    setValue('');
    onClose();
  };

  return (
    <div className="sres-overlay" role="dialog" aria-modal="true" aria-label="제품 검색">
      <button type="button" className="sres-overlay-close" onClick={onClose} aria-label="검색창 닫기">
        ×
      </button>
      <form className="sres-overlay-form" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          className="sres-overlay-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="제품명, 브랜드명, 카테고리로 검색"
          autoComplete="off"
        />
        <span className="sres-overlay-hint">Enter로 검색 · Esc로 닫기</span>
      </form>
    </div>
  );
}
