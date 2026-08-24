import HamburgerIcon from '../icons/HamburgerIcon';

interface HamburgerButtonProps {
  onClick: () => void;
}

/**
 * 화면 왼쪽 상단에 고정되는 햄버거(≡) 버튼 — 마이페이지 진입점.
 * 검색 결과가 떠서 PinnedSearchBar(z-index:45)가 함께 보일 때도 항상 눌러야 해서
 * 그보다 위, 오버레이(z-index:50)보다는 아래로 z-index를 잡는다 (App.css 참고).
 */
export default function HamburgerButton({ onClick }: HamburgerButtonProps) {
  return (
    <button type="button" className="hamburger-btn" onClick={onClick} aria-label="마이페이지 열기">
      <HamburgerIcon />
    </button>
  );
}
