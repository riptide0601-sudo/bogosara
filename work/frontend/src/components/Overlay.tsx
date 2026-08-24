import { useEffect, useRef, type ReactNode } from 'react';

interface OverlayProps {
  id: string;
  titleId: string;
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

/**
 * 공용 오버레이(모달) 뼈대 — 검색/스캔 오버레이가 공유한다.
 * 페이지 이동 없이 배경 딤 + 패널 fade/slide-in 으로 뜨고, X버튼/배경클릭/ESC로 닫힌다.
 *
 * 항상 DOM에 렌더링된 채로 `open` 여부에 따라 `is-open` 클래스만 토글한다.
 * (조건부 마운트를 쓰면 닫힐 때 fade-out 트랜지션이 재생되지 않기 때문)
 */
export default function Overlay({ id, titleId, title, open, onClose, children }: OverlayProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const lastFocused = useRef<HTMLElement | null>(null);

  // 열릴 때: 이전 포커스 저장 + 배경 스크롤 잠금 + 패널 안으로 포커스 이동
  // 닫힐 때: 스크롤 잠금 해제 + 원래 포커스 복원
  useEffect(() => {
    if (open) {
      lastFocused.current = document.activeElement as HTMLElement | null;
      document.body.style.overflow = 'hidden';
      const focusTarget = panelRef.current?.querySelector<HTMLElement>(
        'input, button:not([data-close])',
      );
      focusTarget?.focus();
    } else {
      document.body.style.overflow = '';
      lastFocused.current?.focus();
    }
  }, [open]);

  // ESC 키로 닫기 (열려있을 때만 리스너 등록)
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  return (
    <div
      id={id}
      className={`overlay${open ? ' is-open' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-hidden={!open}
      onClick={(e) => {
        // 딤 배경(패널 바깥) 클릭 시에만 닫기
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="overlay-panel" ref={panelRef}>
        <button
          type="button"
          className="close-btn"
          data-close
          onClick={onClose}
          aria-label={`${title} 닫기`}
        >
          ✕
        </button>
        <h2 className="overlay-title" id={titleId}>
          <span className="cursor">▶</span>
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}
