import { useState } from 'react';
import { Link } from 'react-router-dom';

/**
 * 검색결과/결과 화면 왼쪽 사이드바 — BOGOSARA(홈) / 마이페이지 / 조합보기 3개 진입점.
 * results-section(SearchResultsPage)과 result-view(ResultView) 양쪽에서 공용으로 쓴다.
 * 우선은 항상 떠 있는 바 대신, 왼쪽 위 버튼을 눌러야 열리는 토글 방식으로 둔다 — 열리면
 * 본문 위에 오버레이로 뜬다(본문 레이아웃을 밀어내지 않는다).
 */
export default function SiteSidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="site-sidebar-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? '메뉴 닫기' : '메뉴 열기'}
      >
        {open ? '✕' : '☰'}
      </button>

      {open && (
        <nav className="site-sidebar" aria-label="주요 메뉴">
          <Link className="site-sidebar__link site-sidebar__link--brand" to="/" onClick={() => setOpen(false)}>
            BOGOSARA
          </Link>
          <Link className="site-sidebar__link" to="/mypage" onClick={() => setOpen(false)}>
            마이페이지
          </Link>
          <Link className="site-sidebar__link" to="/routine" onClick={() => setOpen(false)}>
            조합보기
          </Link>
        </nav>
      )}
    </>
  );
}
