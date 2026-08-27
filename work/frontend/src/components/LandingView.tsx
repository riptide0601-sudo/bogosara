import { useEffect, useRef } from 'react';
import HamburgerButton from './HamburgerButton';
import '../LandingView.css';

interface LandingViewProps {
  /** 왼쪽(SEARCH) 영역 클릭 → App.tsx가 실제 검색 오버레이(SearchOverlay)를 연다. */
  onOpenSearch: () => void;
  /** 오른쪽(SCAN) 영역 클릭 → App.tsx가 실제 스캔 오버레이(ScanOverlay)를 연다. */
  onOpenScan: () => void;
  /** 왼쪽 상단 햄버거(≡) → 마이페이지 진입 (다른 화면들과 동일한 진입점). */
  onOpenMyPage: () => void;
}

const SCAN_PAIRS = [
  '나이아신아마이드 → 톤 케어',
  '글리세린 → 보습',
  '아데노신 → 주름 개선',
  '소듐하이알루로네이트 → 수분 보습',
  '잔탄검 → 점도 조절',
];

/**
 * 보고사라 랜딩 화면(첫 화면) — bogo1의 BOGOSARA_landing.html 히어로만 옮겼다(문제/흐름/증명
 * 소개 섹션은 제외). 마우스가 화면 왼쪽에 있으면 돋보기(SEARCH), 오른쪽에 있으면 스캐너(SCAN)
 * 커서 효과가 뜨고, 그 상태에서 클릭하면 실제로 해당 기능이 열린다 — 원본은 정적 소개 페이지라
 * 이 효과가 그냥 시각 연출이었지만, 여기서는 실제 검색/스캔 진입점 역할을 한다.
 *
 * 다른 화면(ResultView/SearchOverlay/ScanOverlay/MyPageView 등) 파일은 이 작업에서 전혀
 * 건드리지 않는다 — 이 컴포넌트는 App.tsx의 랜딩 반환 블록 하나만 대체한다.
 */
export default function LandingView({ onOpenSearch, onOpenScan, onOpenMyPage }: LandingViewProps) {
  const heroRef = useRef<HTMLElement>(null);
  const heroContentRef = useRef<HTMLDivElement>(null);
  const zoomLayerRef = useRef<HTMLDivElement>(null);
  const lensRef = useRef<HTMLDivElement>(null);
  const scannerRef = useRef<HTMLDivElement>(null);
  const scannerLabelRef = useRef<HTMLSpanElement>(null);

  // ---- 커서 추적 돋보기/스캐너 효과 (정교한 마우스 호버가 가능한 기기에서만) ----
  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const fineHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (!fineHover) return;

    const hero = heroRef.current;
    const heroContent = heroContentRef.current;
    const zoomLayer = zoomLayerRef.current;
    const lens = lensRef.current;
    const scanner = scannerRef.current;
    const scannerLabel = scannerLabelRef.current;
    if (!hero || !heroContent || !zoomLayer || !lens || !scanner || !scannerLabel) return;

    // 히어로 내용을 확대 레이어에 복제해둔다 — 렌즈가 그 위를 지나가며 확대해 보여준다.
    zoomLayer.innerHTML = heroContent.innerHTML;
    zoomLayer.setAttribute('aria-hidden', 'true');
    try {
      (zoomLayer as HTMLDivElement & { inert?: boolean }).inert = true;
    } catch {
      // 구형 브라우저는 inert 미지원 — aria-hidden만으로도 충분하다.
    }
    hero.classList.add('has-cursor-fx');

    let rafId: number | null = null;
    let lastX = 0;
    let lastY = 0;
    let scanTimer: ReturnType<typeof setInterval> | null = null;
    let scanIdx = 0;

    const render = () => {
      rafId = null;
      const rect = hero.getBoundingClientRect();
      const x = lastX;
      const y = lastY;
      const half = rect.width / 2;
      const zone = x < half ? 'search' : 'scan';
      hero.dataset.zone = zone;

      if (zone === 'search') {
        lens.style.opacity = '1';
        scanner.style.opacity = '0';
        lens.style.transform = `translate(${x}px,${y}px)`;
        const xPct = (x / rect.width) * 100;
        const yPct = (y / rect.height) * 100;
        zoomLayer.style.transformOrigin = `${xPct}% ${yPct}%`;
        zoomLayer.style.transform = 'scale(1.9)';
        zoomLayer.style.clipPath = `circle(84px at ${x}px ${y}px)`;
        zoomLayer.style.opacity = '1';
        if (scanTimer) {
          clearInterval(scanTimer);
          scanTimer = null;
        }
      } else {
        scanner.style.opacity = '1';
        lens.style.opacity = '0';
        zoomLayer.style.opacity = '0';
        scanner.style.transform = `translate(${x}px,${y}px)`;
        if (!scanTimer) {
          scannerLabel.textContent = SCAN_PAIRS[scanIdx];
          if (!reduceMotion) {
            scanTimer = setInterval(() => {
              scanIdx = (scanIdx + 1) % SCAN_PAIRS.length;
              scannerLabel.textContent = SCAN_PAIRS[scanIdx];
            }, 1500);
          }
        }
      }
    };

    const handlePointerMove = (e: PointerEvent) => {
      const rect = hero.getBoundingClientRect();
      lastX = e.clientX - rect.left;
      lastY = e.clientY - rect.top;
      if (!rafId) rafId = requestAnimationFrame(render);
    };

    const handlePointerLeave = () => {
      lens.style.opacity = '0';
      scanner.style.opacity = '0';
      zoomLayer.style.opacity = '0';
      hero.dataset.zone = '';
      if (scanTimer) {
        clearInterval(scanTimer);
        scanTimer = null;
      }
    };

    hero.addEventListener('pointermove', handlePointerMove);
    hero.addEventListener('pointerleave', handlePointerLeave);

    return () => {
      hero.removeEventListener('pointermove', handlePointerMove);
      hero.removeEventListener('pointerleave', handlePointerLeave);
      if (rafId) cancelAnimationFrame(rafId);
      if (scanTimer) clearInterval(scanTimer);
    };
  }, []);

  /** 히어로 아무 데나 클릭 — 클릭 x좌표가 왼쪽 절반이면 검색, 오른쪽 절반이면 스캔을 연다.
   * 위 커서 효과가 보여주는 "지금 어느 존인지"와 정확히 같은 기준(가로 중앙 기준 절반)이라
   * 사용자가 본 효과 그대로 클릭한 결과가 나온다. */
  const handleHeroClick = (e: React.MouseEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x < rect.width / 2) onOpenSearch();
    else onOpenScan();
  };

  return (
    <div className="landing-view">
      <HamburgerButton onClick={onOpenMyPage} />

      <header className="landing-topbar">
        <span className="landing-mark">BOGOSARA</span>
      </header>

      <section className="landing-hero" ref={heroRef} onClick={handleHeroClick}>
        <div className="landing-hero-inner" ref={heroContentRef}>
          <button
            type="button"
            className="landing-edge-label landing-edge-label--left"
            onClick={(e) => {
              e.stopPropagation();
              onOpenSearch();
            }}
          >
            SEARCH
          </button>
          <button
            type="button"
            className="landing-edge-label landing-edge-label--right"
            onClick={(e) => {
              e.stopPropagation();
              onOpenScan();
            }}
          >
            SCAN
          </button>

          <div className="landing-hero-center">
            <div className="landing-burst" aria-hidden="true">
              <div className="landing-blob" />
              <span className="landing-w landing-w1">정제수</span>
              <span className="landing-w landing-w2 on">나이아신아마이드</span>
              <span className="landing-w landing-w3">부틸렌글라이콜</span>
              <span className="landing-w landing-w4">에틸헥실글리세린</span>
              <span className="landing-w landing-w5 on">소듐하이알루로네이트</span>
              <span className="landing-w landing-w6">다이소듐이디티에이</span>
              <span className="landing-w landing-w7">아데노신</span>
              <span className="landing-w landing-w8 on">글리세린</span>
              <span className="landing-w landing-w9">잔탄검</span>
              <span className="landing-w landing-w10">하이드록시아세토페논</span>
              <span className="landing-w landing-w11">다이프로필렌글라이콜</span>
              <span className="landing-w landing-w12">하이알루로닉애씨드</span>
            </div>

            <h1 className="landing-wordmark" aria-label="BOGOSARA">
              <span className="landing-wm-line landing-wm-line--a" aria-hidden="true">
                BOGO
              </span>
              <span className="landing-wm-line landing-wm-line--b" aria-hidden="true">
                SARA
              </span>
            </h1>

            <p className="landing-hero-tagline">
              검색하거나 찍으면,
              <br />
              복잡한 전성분을 소비자의 언어로.
            </p>
          </div>

          {/* 정교한 호버가 안 되는 기기(터치 등)용 — 왼쪽 절반/오른쪽 절반 클릭 감지 대신
              명시적인 버튼으로 검색/스캔을 실제로 연다. */}
          <div className="landing-mobile-entry">
            <button
              type="button"
              className="landing-entry-card"
              onClick={(e) => {
                e.stopPropagation();
                onOpenSearch();
              }}
            >
              <span className="landing-ic">⌕</span>
              <span>
                <span>SEARCH</span>
                <span className="landing-sub">제품명으로 찾기</span>
              </span>
            </button>
            <button
              type="button"
              className="landing-entry-card"
              onClick={(e) => {
                e.stopPropagation();
                onOpenScan();
              }}
            >
              <span className="landing-ic">▣</span>
              <span>
                <span>SCAN</span>
                <span className="landing-sub">전성분표 촬영하기</span>
              </span>
            </button>
          </div>
        </div>

        <div className="landing-hero-inner landing-hero-zoom-layer" ref={zoomLayerRef} aria-hidden="true" />

        <div className="landing-cursor-fx">
          <div className="landing-lens" ref={lensRef}>
            <div className="landing-lens-crosshair" />
          </div>
          <div className="landing-scanner" ref={scannerRef}>
            <div className="landing-scan-corner tl" />
            <div className="landing-scan-corner tr" />
            <div className="landing-scan-corner bl" />
            <div className="landing-scan-corner br" />
            <div className="landing-scan-line" />
            <span className="landing-scanner-label" ref={scannerLabelRef}>
              OCR SCANNING
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
