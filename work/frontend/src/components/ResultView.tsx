import { useEffect, useState } from 'react';
import { loadIngredientResult, type IngredientResult, type IngredientResultRequest } from '../data/ingredientResult';
import PhotoPanel from './PhotoPanel';
import ResultCard from './ResultCard';
import HamburgerButton from './HamburgerButton';
import Overlay from './Overlay';
import SaveIcon from '../icons/SaveIcon';
import '../ResultView.css';

interface ResultViewProps {
  request: IngredientResultRequest;
  onBack: () => void;
  /** 왼쪽 상단 ≡ 버튼 클릭 → 마이페이지로 이동 (App.tsx가 결과 화면을 닫고 마이페이지를 연다). */
  onOpenMyPage: () => void;
}

type LoadStatus = 'loading' | 'done' | 'error';

/**
 * 검색 리스트 클릭 / 스캔 OCR 성공 두 진입점이 도착하는 결과 화면.
 * 오버레이가 아니라 페이지 전환으로 다룬다 — 전성분 리스트가 길어 스크롤이 깊고,
 * 뒤로가기로 자연스럽게 나갈 수 있어야 하기 때문 (App.tsx 참고).
 *
 * request만 받아 내부에서 로딩 → 성공/실패를 직접 관리한다. 진입 경로(source)에 따라
 * 로딩·에러 문구만 갈라지고, 성공 시 렌더링하는 데이터 형태(IngredientResult)는 동일하다.
 */
export default function ResultView({ request, onBack, onOpenMyPage }: ResultViewProps) {
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [data, setData] = useState<IngredientResult | null>(null);
  // 로그인/회원가입이 아직 없어서(App.tsx·CLAUDE.md 참고) 저장 버튼을 누르면 실제로 저장하는
  // 대신 "로그인이 필요하다"는 팝업만 띄운다. TODO: 로그인 연동 후 — 로그인 상태면 바로 저장
  // (마이페이지 저장한 결과에 추가), 비로그인이면 로그인/회원가입 화면으로 유도.
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setData(null);

    loadIngredientResult(request)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setStatus('done');
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('[보고사라][결과 화면] 데이터 로드 실패', err);
        setStatus('error');
      });

    return () => {
      cancelled = true;
    };
  }, [request]);

  const isScan = request.source === 'scan';

  return (
    <div className="result-view">
      {/* 왼쪽 상단 고정 — 마이페이지 진입점(≡), 랜딩 화면과 동일한 위치/스타일 (App.css 참고) */}
      <HamburgerButton onClick={onOpenMyPage} />

      <header className="result-topbar result-topbar--below-hamburger">
        <button type="button" className="result-back-btn" onClick={onBack}>
          <span className="cursor">◀</span>
          {isScan ? '다시 스캔하기' : '검색으로 돌아가기'}
        </button>
        {/* 사진 상자 오른쪽 선에 맞춰 정렬되는 정사각형 저장 버튼 (아래 result-layout과 같은
            칼럼 트랙을 쓰는 그리드라 자연히 맞춰진다 — ResultView.css 참고) */}
        <button type="button" className="result-save-btn" onClick={() => setShowLoginPopup(true)} aria-label="결과 저장하기">
          <SaveIcon />
        </button>
      </header>

      <Overlay
        id="overlay-save-login"
        titleId="overlay-save-login-title"
        title="로그인이 필요해요"
        open={showLoginPopup}
        onClose={() => setShowLoginPopup(false)}
      >
        <p className="overlay-message">
          결과를 저장하려면 로그인이 필요해요. 로그인/회원가입 기능은 아직 준비 중이에요.
        </p>
      </Overlay>

      {status === 'loading' && (
        <div className="result-loading" role="status" aria-live="polite">
          <p className="result-loading-text">{isScan ? '성분표 분석 중...' : '제품 정보를 불러오는 중...'}</p>
          <div className="result-skeleton-block" aria-hidden="true" />
          <div className="result-skeleton-block" aria-hidden="true" />
        </div>
      )}

      {status === 'error' && (
        <div className="result-error-box" role="alert">
          <p className="result-error-title">
            {isScan ? '성분표를 인식하지 못했어요' : '정보를 불러오지 못했어요'}
          </p>
          <p className="result-error-body">
            {isScan
              ? '빛 반사나 흐릿함 때문일 수 있어요. 성분표 전체가 잘 보이도록 다시 찍어주세요.'
              : '네트워크 상태를 확인하고 다시 시도해주세요.'}
          </p>
          <button type="button" className="btn-primary" onClick={onBack}>
            {isScan ? '다시 스캔하기' : '돌아가기'}
          </button>
        </div>
      )}

      {status === 'done' && data && (
        <div className="result-layout">
          <PhotoPanel request={request} productName={data.product.product_name} />
          <ResultCard product={data.product} ingredients={data.ingredients} isScan={isScan} />
        </div>
      )}
    </div>
  );
}
