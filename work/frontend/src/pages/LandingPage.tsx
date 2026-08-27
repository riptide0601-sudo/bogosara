import { useState } from 'react';
import BackgroundSparkles from '../components/BackgroundSparkles';
import LandingHero from '../components/LandingHero';
import { SearchOverlay } from '../components/SearchOverlay';
import { ScanOverlay } from '../components/ScanOverlay';

type OverlayKind = 'search' | 'scan' | null;

/**
 * 보고사라 랜딩 페이지 — 히어로 화면 하나로 꽉 채운다 (마이페이지/조합 바로가기 버튼은 없앴다).
 * 돋보기(검색) / 스캐너(OCR) 두 아이콘 중 하나를 고르면 페이지 이동 없이 전체화면 오버레이가
 * 뜬다(SearchOverlay/ScanOverlay는 자체적으로 mount될 때만 렌더되는 구조라 open prop이 없다 —
 * 아래 activeOverlay 값에 따라 조건부 렌더링으로 열고 닫는다).
 * 검색을 제출하면 전용 검색 결과 페이지(/search?q=...)로 이동한다.
 */
export default function LandingPage() {
  const [activeOverlay, setActiveOverlay] = useState<OverlayKind>(null);

  const closeOverlay = () => setActiveOverlay(null);

  return (
    <>
      {/* 배경 여백을 채우는 떠다니는 픽셀 반짝임(별/거품) — 순수 장식 */}
      <BackgroundSparkles />

      <LandingHero
        onSearchClick={() => setActiveOverlay('search')}
        onScanClick={() => setActiveOverlay('scan')}
      />

      {/* 돋보기(검색) 오버레이 — 제출하면 /search로 이동 후 자동으로 닫힌다 */}
      {activeOverlay === 'search' && <SearchOverlay onClose={closeOverlay} />}

      {/* 스캐너 오버레이 — 실제 웹캠 라이브 프리뷰. 캡처 성공 시 /scan-result로 이동 후 자동으로 닫힌다 */}
      {activeOverlay === 'scan' && <ScanOverlay onClose={closeOverlay} />}
    </>
  );
}
