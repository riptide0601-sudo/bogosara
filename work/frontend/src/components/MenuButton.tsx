import type { ReactNode } from 'react';

interface MenuButtonProps {
  id: string;
  label: string;
  ariaControls: string;
  onClick: () => void;
  icon: ReactNode;
  variant: 'search' | 'scan';
}

/**
 * 시작 메뉴의 아이콘 버튼 (돋보기 / 스캐너 공용).
 * 호버·포커스 시 CSS에서 바운스 + ▶ 커서 피드백을 준다 (App.css 참고).
 */
export default function MenuButton({ id, label, ariaControls, onClick, icon, variant }: MenuButtonProps) {
  return (
    <button
      type="button"
      id={id}
      className={`menu-item menu-item--${variant}`}
      aria-haspopup="dialog"
      aria-controls={ariaControls}
      onClick={onClick}
    >
      <span className="icon-frame">{icon}</span>
      <span className="menu-label">
        <span className="cursor">▶</span>
        {label}
      </span>
    </button>
  );
}
