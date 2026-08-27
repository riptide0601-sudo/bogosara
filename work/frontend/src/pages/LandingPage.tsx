import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import BackgroundSparkles from '../components/BackgroundSparkles';
import LandingView from '../components/LandingView';
import SearchOverlay from '../components/SearchOverlay';
import ScanOverlay from '../components/ScanOverlay';
import ResultsSection, { type SearchStatus } from '../components/ResultsSection';
import { useAuth } from '../context/AuthContext';
import CreamJarIcon from '../icons/CreamJarIcon';
import { searchProducts } from '../api';
import type { Product } from '../data/mockProducts';

type OverlayKind = 'search' | 'scan' | null;

/**
 * 보고사라 랜딩 페이지.
 * 돋보기(검색) / 스캐너(OCR) 두 아이콘 중 하나를 고르면 페이지 이동 없이
 * 오버레이가 뜬다 — 검색 결과는 페이지 이동 없이 같은 화면 아래쪽에 나타나고,
 * 결과 카드를 클릭하거나 스캔에 성공하면 그때 /product/:id · /scan-result로 이동한다.
 */
export default function LandingPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeOverlay, setActiveOverlay] = useState<OverlayKind>(null);

  // ---- 검색 결과 상태 ----
  const [searchStatus, setSearchStatus] = useState<SearchStatus>('idle');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const resultsRef = useRef<HTMLElement>(null);

  const closeOverlay = () => setActiveOverlay(null);

  /** 랜딩의 "내 화장품 조합" 바로가기 — 로그인 상태면 곧장 /routine으로, 아니면 로그인
   * 화면(/mypage가 비로그인 시 보여주는 화면)으로 보낸다. */
  const handleOpenRoutine = () => {
    if (user) navigate('/routine');
    else navigate('/mypage');
  };

  /** 검색 실행 — GET /products?query=... 를 호출해 실제 DB 결과를 보여준다. */
  const runSearch = (query: string) => {
    setSearchQuery(query);
    setSearchStatus('loading');

    searchProducts(query)
      .then((results) => {
        setSearchResults(results);
        setSearchStatus('done');

        // 결과가 그려진 다음 프레임에 결과 섹션으로 부드럽게 스크롤
        requestAnimationFrame(() => {
          resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      })
      .catch((err) => {
        console.error('[보고사라][검색] API 호출 실패', err);
        setSearchResults([]);
        setSearchStatus('done');
      });
  };

  /** 검색 결과 카드 클릭 → 결과 화면 진입 (검색 진입점) */
  const handleSelectProduct = (product: Product) => {
    navigate(`/product/${product.id}`);
  };

  /** 스캔 캡처 성공 → 오버레이 닫고 결과 화면 진입 (스캔 진입점) */
  const handleScanCaptured = (dataUrl: string) => {
    closeOverlay();
    navigate('/scan-result', { state: { image: dataUrl } });
  };

  return (
    <>
      {/* 배경 여백을 채우는 떠다니는 픽셀 반짝임(별/거품) — 순수 장식 */}
      <BackgroundSparkles />

      {/* 마이페이지 진입점(≡)은 LandingView가 내부에서 직접 그린다 — 그 바로 아래
          내 화장품 조합 바로가기만 여기서 얹는다(고정 위치라 DOM 트리 위치는 무관). */}
      <button
        type="button"
        className="hamburger-btn quick-routine-btn"
        onClick={handleOpenRoutine}
        aria-label="내 화장품 조합 바로가기"
      >
        <CreamJarIcon />
      </button>

      <LandingView
        onOpenSearch={() => setActiveOverlay('search')}
        onOpenScan={() => setActiveOverlay('scan')}
        onOpenMyPage={() => navigate('/mypage')}
      />

      {/* 검색 결과 / 제품 리스트 — 페이지 이동 없이 같은 페이지 아래쪽에 나타난다 */}
      <ResultsSection
        ref={resultsRef}
        status={searchStatus}
        query={searchQuery}
        results={searchResults}
        onSelectProduct={handleSelectProduct}
        onSearch={runSearch}
      />

      {/* 돋보기(검색) 오버레이 — 페이지 이동 없이 떠오르는 검색바 */}
      <SearchOverlay open={activeOverlay === 'search'} onClose={closeOverlay} onSearch={runSearch} />

      {/* 스캐너 오버레이 — 실제 웹캠 라이브 프리뷰. 캡처 성공 시 결과 화면(OCR 분석 중 → 결과)으로 이어진다 */}
      <ScanOverlay open={activeOverlay === 'scan'} onClose={closeOverlay} onCaptured={handleScanCaptured} />
    </>
  );
}
