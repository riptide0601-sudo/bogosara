import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import BackgroundSparkles from '../components/BackgroundSparkles';
import ResultView from '../components/ResultView';
import SiteSidebar from '../components/SiteSidebar';
import type { OcrAnalyzeResult } from '../api';
import type { Product } from '../data/mockProducts';

interface ScanRouteState {
  image?: string;
  ocr?: OcrAnalyzeResult;
}

/** 스캔 캡처 완료(/scan-result, ScanOverlay가 넘긴 router state) 진입점. */
export default function ScanResultPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { image, ocr } = (location.state as ScanRouteState | null) ?? {};

  // 캡처 직후가 아니면(예: 새로고침, 낯선 진입) 랜딩으로 돌려보낸다. ocr까지 있어야
  // ResultView가 실제로 결과를 그릴 수 있다(ScanOverlay는 인식 성공 시에만 넘어온다).
  if (!image || !ocr) return <Navigate to="/" replace />;

  return (
    <>
      <BackgroundSparkles />
      <SiteSidebar />
      <ResultView
        request={{ source: 'scan', imageDataUrl: image, ocr }}
        onBack={() => navigate(-1)}
        onOpenMyPage={() => navigate('/mypage')}
        onSelectProduct={(product: Product) => navigate(`/product/${product.id}`)}
      />
    </>
  );
}
