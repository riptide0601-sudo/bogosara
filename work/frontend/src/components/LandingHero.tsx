import { useEffect, useRef } from 'react';
import '../LandingHero.css';

interface LandingHeroProps {
  onSearchClick: () => void;
  onScanClick: () => void;
}

const BURST_WORDS: { text: string; className: string; on?: boolean }[] = [
  { text: '정제수', className: 'w1' },
  { text: '나이아신아마이드', className: 'w2', on: true },
  { text: '부틸렌글라이콜', className: 'w3' },
  { text: '에틸헥실글리세린', className: 'w4' },
  { text: '소듐하이알루로네이트', className: 'w5', on: true },
  { text: '다이소듐이디티에이', className: 'w6' },
  { text: '아데노신', className: 'w7' },
  { text: '글리세린', className: 'w8', on: true },
  { text: '잔탄검', className: 'w9' },
  { text: '하이드록시아세토페논', className: 'w10' },
  { text: '다이프로필렌글라이콜', className: 'w11' },
  { text: '하이알루로닉애씨드', className: 'w12' },
];

const SCAN_PAIRS = [
  '나이아신아마이드 → 톤 케어',
  '글리세린 → 보습',
  '아데노신 → 주름 개선',
  '소듐하이알루로네이트 → 수분 보습',
  '잔탄검 → 점도 조절',
];

/** 워드마크 + 성분 단어 burst + 카피 + 안내문 — 참고 디자인처럼 블롭(초록 원) 안쪽에
 * 워드마크 → 카피 → 안내문 순서로 겹쳐서 들어간다. */
function HeroWordmark({ onSearchClick, onScanClick }: LandingHeroProps) {
  return (
    <div className="lh-hero-center">
      <div className="lh-burst" aria-hidden="true">
        <div className="lh-blob" />
        {BURST_WORDS.map((w) => (
          <span key={w.className} className={`lh-w lh-${w.className}${w.on ? ' lh-w-on' : ''}`}>
            {w.text}
          </span>
        ))}
      </div>
      <h1 className="lh-wordmark" aria-label="BOGOSARA">
        <span className="lh-wm-line lh-wm-line--a" aria-hidden="true">
          BOGO
        </span>
        <span className="lh-wm-line lh-wm-line--b" aria-hidden="true">
          SARA
        </span>
      </h1>
      <p className="lh-instruction">
        <button
          type="button"
          className="lh-instruction-link"
          onClick={(e) => {
            e.stopPropagation();
            onSearchClick();
          }}
        >
          왼쪽
        </button>
        은 검색,{' '}
        <button
          type="button"
          className="lh-instruction-link"
          onClick={(e) => {
            e.stopPropagation();
            onScanClick();
          }}
        >
          오른쪽
        </button>
        은 스캔이에요 —
        <br />
        커서를 옮겨보세요.
      </p>
    </div>
  );
}

/** 워드마크(+카피+안내문) + SEARCH/SCAN 카드를 한 그룹으로 묶어서, 실제 레이어와 돋보기 확대
 * 레이어 양쪽에 똑같이 쓴다 — 렌즈 아래로 보이는 확대 이미지가 실제 레이아웃과 정확히
 * 겹치게 하기 위함. */
function HeroMiddle({ onSearchClick, onScanClick }: LandingHeroProps) {
  return (
    <div className="lh-hero-middle">
      <HeroWordmark onSearchClick={onSearchClick} onScanClick={onScanClick} />
    </div>
  );
}

/**
 * 보고사라 랜딩 히어로 — 참고 디자인(BOGOSARA_landing.html)의 중앙 워드마크·커서 연출·서체를
 * 우리 앱 배경(크림 + CRT 스캔라인) 위에 얹은 버전.
 *
 * 파인 포인터(마우스) 환경에서는 화면을 좌/우로 나눠 왼쪽엔 돋보기 렌즈, 오른쪽엔 OCR 스캐너
 * 커서를 띄우고, 렌즈 안쪽은 워드마크를 확대해서 보여준다(heroZoomLayer). 클릭하면 그 위치가
 * 속한 절반에 따라 검색/스캔이 바로 열린다. SEARCH/SCAN 카드(lh-entry-row)는 이 커서 연출과
 * 별개로 모든 기기에서 항상 보이는 명시적 진입점이다.
 */
export default function LandingHero({ onSearchClick, onScanClick }: LandingHeroProps) {
  const heroRef = useRef<HTMLElement>(null);
  const zoomLayerRef = useRef<HTMLDivElement>(null);
  const lensRef = useRef<HTMLDivElement>(null);
  const scannerRef = useRef<HTMLDivElement>(null);
  const scannerLabelRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const fineHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (!fineHover) return;

    const hero = heroRef.current;
    const zoomLayer = zoomLayerRef.current;
    const lens = lensRef.current;
    const scanner = scannerRef.current;
    const scannerLabel = scannerLabelRef.current;
    if (!hero || !zoomLayer || !lens || !scanner || !scannerLabel) return;

    hero.classList.add('lh-has-cursor-fx');

    let rafId: number | null = null;
    let lastX = 0;
    let lastY = 0;
    let scanIdx = 0;
    let scanTimer: ReturnType<typeof setInterval> | null = null;

    const render = () => {
      rafId = null;
      const rect = hero.getBoundingClientRect();
      const x = lastX;
      const y = lastY;
      const zone = x < rect.width / 2 ? 'search' : 'scan';
      hero.dataset.zone = zone;

      if (zone === 'search') {
        lens.style.opacity = '1';
        scanner.style.opacity = '0';
        lens.style.transform = `translate(${x}px, ${y}px)`;
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
        scanner.style.transform = `translate(${x}px, ${y}px)`;
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

  /** 히어로 어디를 클릭하든(SEARCH/SCAN 카드 제외 — 자체 onClick으로 처리) 클릭 지점이 속한
   * 절반 기준으로 검색/스캔 진입 — 위 커서 연출이 "미리보기", 클릭이 "확정"인 구조. */
  const handleHeroClick = (e: React.MouseEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x < rect.width / 2) onSearchClick();
    else onScanClick();
  };

  return (
    <section className="lh-hero" id="lhHero" ref={heroRef} onClick={handleHeroClick}>
      <span className="lh-edge-label lh-edge-label--left" aria-hidden="true">
        SEARCH
      </span>
      <span className="lh-edge-label lh-edge-label--right" aria-hidden="true">
        SCAN
      </span>

      <div className="lh-hero-inner">
        <span className="lh-mark">BOGOSARA</span>
        <HeroMiddle onSearchClick={onSearchClick} onScanClick={onScanClick} />
      </div>

      <div className="lh-hero-inner lh-hero-zoom" ref={zoomLayerRef} aria-hidden="true" inert={true}>
        <HeroMiddle onSearchClick={onSearchClick} onScanClick={onScanClick} />
      </div>

      <div className="lh-cursor-fx" aria-hidden="true">
        <div className="lh-lens" ref={lensRef}>
          <div className="lh-lens-crosshair" />
        </div>
        <div className="lh-scanner" ref={scannerRef}>
          <div className="lh-scan-corner tl" />
          <div className="lh-scan-corner tr" />
          <div className="lh-scan-corner bl" />
          <div className="lh-scan-corner br" />
          <div className="lh-scan-line" />
          <span className="lh-scanner-label" ref={scannerLabelRef}>
            OCR SCANNING
          </span>
        </div>
      </div>
    </section>
  );
}
