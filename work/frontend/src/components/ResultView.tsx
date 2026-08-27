import { useEffect, useState } from 'react';
import { loadIngredientResult, type IngredientResult, type IngredientResultRequest } from '../data/ingredientResult';
import type { Product } from '../data/mockProducts';
import { fetchProductFamilyRank, fetchSkinFit, type FamilyRankInfo } from '../api';
import { ApiError } from '../api/client';
import { getSkinProfile, saveResult } from '../api/users';
import { useAuth } from '../context/AuthContext';
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
  /** PhotoPanel의 추천 제품 클릭 → 그 제품으로 결과 화면을 다시 로드 (App.tsx의 handleSelectProduct). */
  onSelectProduct: (product: Product) => void;
}

type LoadStatus = 'loading' | 'done' | 'error';

export interface SkinRiskItem {
  skinType: string;
  ingredients: { name: string; reason: string }[];
}

/** 로그인한 유저의 마이페이지 피부 타입 기준 개인화된 위험 성분 정보 (ResultSummaryPanel에
 * "내 피부 타입 기준" 섹션으로 전달됨). 비로그인/피부타입 미등록이면 그 상태를 그대로 넘겨서
 * ResultSummaryPanel이 로그인·설정을 유도하는 문구를 보여줄 수 있게 한다. */
export type SkinRiskInfo =
  | { status: 'signed-out' }
  | { status: 'no-skin-type' }
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ok'; risks: SkinRiskItem[] };

/** "비슷한 제품과 비교하면" 카드(ResultSummaryPanel) — GET /products/{id}/family-rank 결과.
 * 한 제품이 여러 계열에 동시에 속할 수 있어(예: 더마토리 히알샷 = 히알루론산+B5) data는 배열.
 * 스캔 진입(source==='scan')은 실재 product_id가 없어 항상 'idle'. 'none'은 이 제품이 어떤
 * 성분 계열에도 속하지 않는 정상 상태(백엔드가 빈 배열)라 에러와 구분해서 섹션을 그냥 숨긴다. */
export type FamilyRankState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'none' }
  | { status: 'error' }
  | { status: 'ok'; data: FamilyRankInfo[] };

/**
 * 검색 리스트 클릭 / 스캔 OCR 성공 두 진입점이 도착하는 결과 화면.
 * 오버레이가 아니라 페이지 전환으로 다룬다 — 전성분 리스트가 길어 스크롤이 깊고,
 * 뒤로가기로 자연스럽게 나갈 수 있어야 하기 때문 (App.tsx 참고).
 *
 * request만 받아 내부에서 로딩 → 성공/실패를 직접 관리한다. 진입 경로(source)에 따라
 * 로딩·에러 문구만 갈라지고, 성공 시 렌더링하는 데이터 형태(IngredientResult)는 동일하다.
 */
export default function ResultView({ request, onBack, onOpenMyPage, onSelectProduct }: ResultViewProps) {
  const { user } = useAuth();
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [data, setData] = useState<IngredientResult | null>(null);
  // 로그인 상태면 저장 버튼 클릭 시 바로 저장(마이페이지 저장한 결과에 추가), 비로그인이면
  // 로그인이 필요하다는 팝업을 띄운다.
  const [showLoginPopup, setShowLoginPopup] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [skinRisk, setSkinRisk] = useState<SkinRiskInfo>({ status: 'signed-out' });
  const [familyRank, setFamilyRank] = useState<FamilyRankState>({ status: 'idle' });

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setData(null);
    setSaved(false);
    setSaveError(null);

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

  // 로그인한 유저의 마이페이지 피부 타입 기준 개인화된 위험 성분 — search 진입(실제 product_id가
  // 있는 경우)에만 의미가 있다. skin-fit은 skin_type을 생략하면 4개 타입 전부 내려주므로,
  // 별도 API 호출 없이 유저의 skin_types와 클라이언트에서 대조한다.
  useEffect(() => {
    if (request.source !== 'search' || !user) {
      setSkinRisk({ status: 'signed-out' });
      return;
    }

    let cancelled = false;
    setSkinRisk({ status: 'loading' });

    getSkinProfile()
      .then((profile) => {
        if (cancelled) return null;
        if (profile.skin_types.length === 0) {
          setSkinRisk({ status: 'no-skin-type' });
          return null;
        }
        return fetchSkinFit(request.productId).then((all) => {
          if (cancelled) return;
          const mySkinTypes = new Set(profile.skin_types);
          const risks = all
            .filter((r) => mySkinTypes.has(r.skin_type) && r.has_risk)
            .map((r) => ({
              skinType: r.skin_type,
              ingredients: r.risk_ingredients.map((i) => ({
                name: i.name_kr ?? '',
                reason: i.reason ?? i.risk_type ?? '',
              })),
            }));
          setSkinRisk({ status: 'ok', risks });
        });
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('[보고사라][결과 화면] 피부 타입별 위험 성분 조회 실패', err);
        setSkinRisk({ status: 'error' });
      });

    return () => {
      cancelled = true;
    };
  }, [request, user]);

  // "비슷한 제품과 비교하면" — search 진입(실제 product_id가 있는 경우)에만 조회한다.
  useEffect(() => {
    if (request.source !== 'search') {
      setFamilyRank({ status: 'idle' });
      return;
    }

    let cancelled = false;
    setFamilyRank({ status: 'loading' });

    fetchProductFamilyRank(request.productId)
      .then((data) => {
        if (cancelled) return;
        setFamilyRank(data.length > 0 ? { status: 'ok', data } : { status: 'none' });
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('[보고사라][결과 화면] 계열 비교 조회 실패', err);
        setFamilyRank({ status: 'error' });
      });

    return () => {
      cancelled = true;
    };
  }, [request]);

  const isScan = request.source === 'scan';

  const handleSaveClick = async () => {
    if (!user) {
      setShowLoginPopup(true);
      return;
    }
    const productId = data?.product.product_id;
    if (!productId) {
      // 스캔 진입은 DB product_id가 없어 저장할 대상이 없다 — 검색 진입에서만 저장 가능.
      setSaveError('스캔 결과는 아직 저장할 수 없어요.');
      return;
    }
    setSaveError(null);
    setSaving(true);
    try {
      await saveResult(productId);
      setSaved(true);
    } catch (err) {
      console.error('[보고사라][결과 화면] 결과 저장 실패', err);
      setSaveError(err instanceof ApiError ? err.message : '저장에 실패했어요. 잠시 후 다시 시도해주세요.');
    } finally {
      setSaving(false);
    }
  };

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
            칼럼 트랙을 쓰는 그리드라 자연히 맞춰진다 — ResultView.css 참고). 로그인 상태면
            바로 저장하고 .is-saved 톤으로 바뀌고, 비로그인이면 로그인 팝업을 띄운다. */}
        <button
          type="button"
          className={`result-save-btn${saved ? ' is-saved' : ''}`}
          onClick={handleSaveClick}
          disabled={saving}
          aria-pressed={saved}
          aria-label={saved ? '저장됨' : '결과 저장하기'}
        >
          <SaveIcon />
        </button>
      </header>

      {saveError && (
        <p className="result-save-error" role="alert">
          {saveError}
        </p>
      )}

      <Overlay
        id="overlay-save-login"
        titleId="overlay-save-login-title"
        title="로그인이 필요해요"
        open={showLoginPopup}
        onClose={() => setShowLoginPopup(false)}
      >
        <p className="overlay-message">결과를 저장하려면 로그인이 필요해요.</p>
        <button
          type="button"
          className="btn-primary"
          onClick={() => {
            setShowLoginPopup(false);
            onOpenMyPage(); // 비로그인 상태에서 마이페이지 진입점을 누르면 App.tsx가 LoginView로 보낸다.
          }}
        >
          로그인하러 가기
        </button>
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
          <PhotoPanel
            request={request}
            productName={data.product.product_name}
            productImageUrl={data.product.image_url}
            recommendedProducts={data.product.recommended_products}
            onSelectProduct={onSelectProduct}
          />
          <ResultCard
            product={data.product}
            ingredients={data.ingredients}
            isScan={isScan}
            skinRisk={skinRisk}
            familyRank={familyRank}
          />
        </div>
      )}
    </div>
  );
}
