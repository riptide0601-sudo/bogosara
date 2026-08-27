import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import BackgroundSparkles from '../components/BackgroundSparkles';
import ResultView from '../components/ResultView';
import type { Product } from '../data/mockProducts';

interface ScanRouteState {
  image?: string;
}

/** 스캔 캡처 완료(/scan-result, ScanOverlay가 넘긴 router state) 진입점. */
export default function ScanResultPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const image = (location.state as ScanRouteState | null)?.image;

  // 캡처 직후가 아니면(예: 새로고침, 낯선 진입) 랜딩으로 돌려보낸다.
  if (!image) return <Navigate to="/" replace />;

  return (
    <>
      <BackgroundSparkles />
      <ResultView
        request={{ source: 'scan', imageDataUrl: image }}
        onBack={() => navigate(-1)}
        onOpenMyPage={() => navigate('/mypage')}
        onSelectProduct={(product: Product) => navigate(`/product/${product.id}`)}
      />
    </>
  );
}
