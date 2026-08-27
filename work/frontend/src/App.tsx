import { useRef, useState } from 'react';
import BackgroundSparkles from './components/BackgroundSparkles';
import WalkingMascot from './components/WalkingMascot';
import LandingHero from './components/LandingHero';
import HamburgerButton from './components/HamburgerButton';
import SearchOverlay from './components/SearchOverlay';
import ScanOverlay from './components/ScanOverlay';
import ResultsSection, { type SearchStatus } from './components/ResultsSection';
import ResultView from './components/ResultView';
import MyPageView from './components/MyPageView';
import RoutineView from './components/RoutineView';
import LoginView from './components/LoginView';
import { useAuth } from './context/AuthContext';
import CosmeticMascotIcon from './icons/CosmeticMascotIcon';
import CreamJarIcon from './icons/CreamJarIcon';
import CushionIcon from './icons/CushionIcon';
import { searchProducts } from './api';
import type { Product } from './data/mockProducts';
import type { SavedResult } from './data/myPage';
import type { IngredientResultRequest } from './data/ingredientResult';
import './App.css';

/** 걸어다니는 캐릭터 행렬 — 화장품 병(리더) 뒤로 수분크림통·쿠션이 쫄래쫄래 따라간다.
 * 셋 다 walkDuration을 같게 줘야 대형이 안 벌어지고, walkDelay만 다르게 줘서
 * 뒤에서 출발하는 것처럼 보이게 한다. */
const WALKING_MASCOTS = [
  { Icon: CosmeticMascotIcon, width: 34, height: 45, bottom: 6, walkDuration: 13, walkDelay: 0, bobDuration: 0.5, restLeft: 20 },
  { Icon: CreamJarIcon, width: 26, height: 24, bottom: 6, walkDuration: 13, walkDelay: 0.35, bobDuration: 0.42, restLeft: 58 },
  { Icon: CushionIcon, width: 20, height: 22, bottom: 6, walkDuration: 13, walkDelay: 0.65, bobDuration: 0.36, restLeft: 88 },
];

type OverlayKind = 'search' | 'scan' | null;

/**
 * 보고사라 랜딩 페이지.
 * 돋보기(검색) / 스캐너(OCR) 두 아이콘 중 하나를 고르면 페이지 이동 없이
 * 오버레이가 뜬다 — 실제 검색·OCR 연동은 각 오버레이 컴포넌트의 TODO 지점에서 이어 붙이면 된다.
 */
export default function App() {
  const { user, initializing } = useAuth();
  const [activeOverlay, setActiveOverlay] = useState<OverlayKind>(null);

  // ---- 검색 결과 상태 (백엔드 미연동 — 목 데이터로 대체) ----
  const [searchStatus, setSearchStatus] = useState<SearchStatus>('idle');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const resultsRef = useRef<HTMLElement>(null);

  // ---- 성분 결과 화면 진입 요청 (검색 리스트 클릭 / 스캔 OCR 성공) ----
  // null이면 랜딩 화면, 값이 있으면 ResultView로 전체 화면이 전환된다. 오버레이가 아니라 화면
  // 전환으로 다루는 이유: 전성분 리스트가 길어 스크롤이 깊고, 뒤로가기로 자연스럽게 나갈 수
  // 있어야 하기 때문 (ResultView.tsx 상단 주석 참고).
  const [resultRequest, setResultRequest] = useState<IngredientResultRequest | null>(null);

  // ---- 마이페이지 진입 상태 ----
  // resultRequest가 있으면 화면 우선순위상 ResultView가 뜨지만, mypageOpen은 그 뒤에서 계속
  // true로 남아있는다 — 저장한 결과를 열어봤다가 뒤로가기를 누르면 마이페이지로 돌아오게 하기
  // 위함(아래 렌더 분기 참고).
  const [mypageOpen, setMypageOpen] = useState(false);

  // ---- 내 화장품 조합 진입 상태 ----
  // mypageOpen과 같은 패턴 — routineOpen이 켜져도 mypageOpen은 그대로 true로 남아있어서,
  // 뒤로가기를 누르면 마이페이지가 남아있던 자리에 다시 나타난다.
  const [routineOpen, setRoutineOpen] = useState(false);

  const closeOverlay = () => setActiveOverlay(null);

  /** 랜딩의 "내 화장품 조합" 바로가기 — 로그인 상태면 곧장 RoutineView로, 아니면 로그인
   * 화면으로 보낸다(RoutineView 자체는 인증 여부를 다시 확인하지 않으므로 여기서 가려야 함).
   * mypageOpen도 같이 켜둬야 RoutineView의 "뒤로가기 → 마이페이지로" 동작이 그대로 맞는다
   * (RoutineView.tsx 상단 주석 참고 — 뒤로가기는 항상 마이페이지로 돌아간다는 전제). */
  const handleOpenRoutine = () => {
    if (user) {
      setMypageOpen(true);
      setRoutineOpen(true);
    } else {
      setMypageOpen(true);
    }
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
    setResultRequest({ source: 'search', productId: product.id, productName: product.name });
  };

  /** 스캔 캡처 성공 → 오버레이 닫고 결과 화면 진입 (스캔 진입점) */
  const handleScanCaptured = (dataUrl: string) => {
    closeOverlay();
    setResultRequest({ source: 'scan', imageDataUrl: dataUrl });
  };

  /** 마이페이지의 "저장한 결과" 카드 클릭 → 결과 화면 진입 (마이페이지는 백그라운드에 유지) */
  const handleSelectSavedResult = (result: SavedResult) => {
    setResultRequest({ source: 'search', productId: result.id, productName: result.productName });
  };

  // 결과 화면 진입 요청이 있으면 (검색/스캔/마이페이지 저장 결과 중 어디서 왔든) 랜딩·마이페이지
  // 대신 ResultView로 전체 화면을 교체한다. mypageOpen은 그대로 유지해서, 뒤로가기를 누르면
  // resultRequest만 비워지고 마이페이지가 남아있던 자리에 다시 나타난다.
  if (resultRequest) {
    return (
      <>
        {/* 성분 설명 페이지(ResultView)에서는 걸어다니는 캐릭터를 빼고 배경 반짝임만 둔다 —
            전성분 리스트를 읽는 화면이라 화면 하단에서 계속 움직이는 캐릭터가 방해된다. */}
        <BackgroundSparkles />
        <ResultView
          request={resultRequest}
          onBack={() => setResultRequest(null)}
          onOpenMyPage={() => {
            setResultRequest(null);
            setMypageOpen(true);
          }}
          onSelectProduct={handleSelectProduct}
        />
      </>
    );
  }

  // 내 화장품 조합 화면 — 로그인 상태에서만 마이페이지의 "내 조합 확인하기"로 들어올 수
  // 있으므로 여기서 다시 로그인 여부를 가릴 필요는 없다. 뒤로가기는 항상 마이페이지로.
  if (routineOpen) {
    return (
      <>
        <BackgroundSparkles />
        <RoutineView onBack={() => setRoutineOpen(false)} />
      </>
    );
  }

  // 마이페이지 진입 상태면 랜딩 대신 MyPageView(로그인 상태) 또는 LoginView(비로그인)로
  // 전체 화면을 교체한다. initializing 동안은(새로고침 직후 저장된 토큰으로 /users/me
  // 조회 중) 로그인 여부를 아직 몰라서 둘 다 그리지 않고 잠깐 비워둔다.
  if (mypageOpen) {
    return (
      <>
        <BackgroundSparkles />
        {WALKING_MASCOTS.map((mascot, i) => (
          <WalkingMascot key={i} {...mascot} />
        ))}
        {!initializing &&
          (user ? (
            <MyPageView
              onBack={() => setMypageOpen(false)}
              onSelectSavedResult={handleSelectSavedResult}
              onOpenRoutine={() => setRoutineOpen(true)}
            />
          ) : (
            <LoginView onBack={() => setMypageOpen(false)} onSuccess={() => {}} />
          ))}
      </>
    );
  }

  return (
    <>
      {/* 배경 여백을 채우는 떠다니는 픽셀 반짝임(별/거품) — 순수 장식 */}
      <BackgroundSparkles />

      {/* 화면 맨 아래를 걸어다니는 화장품 캐릭터들 — 순수 장식 */}
      {WALKING_MASCOTS.map((mascot, i) => (
        <WalkingMascot key={i} {...mascot} />
      ))}

      {/* 왼쪽 상단 고정 — 마이페이지 진입점(≡), 그 아래 내 화장품 조합 바로가기 */}
      <HamburgerButton onClick={() => setMypageOpen(true)} />
      <button
        type="button"
        className="hamburger-btn quick-routine-btn"
        onClick={handleOpenRoutine}
        aria-label="내 화장품 조합 바로가기"
      >
        <CreamJarIcon />
      </button>

      <LandingHero
        onSearchClick={() => setActiveOverlay('search')}
        onScanClick={() => setActiveOverlay('scan')}
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
