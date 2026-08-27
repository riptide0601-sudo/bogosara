import { useNavigate, useParams } from 'react-router-dom';
import BackgroundSparkles from '../components/BackgroundSparkles';
import ResultView from '../components/ResultView';
import SiteSidebar from '../components/SiteSidebar';
import type { Product } from '../data/mockProducts';

/** 검색 결과 카드 클릭(/product/:id) 진입점. */
export default function ProductResultPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  if (!id) return null;

  return (
    <>
      {/* 성분 설명 페이지에서는 걸어다니는 캐릭터를 빼고 배경 반짝임만 둔다 — 전성분 리스트를
          읽는 화면이라 화면 하단에서 계속 움직이는 캐릭터가 방해된다. */}
      <BackgroundSparkles />
      <SiteSidebar />
      <ResultView
        request={{ source: 'search', productId: id, productName: '' }}
        onBack={() => navigate(-1)}
        onOpenMyPage={() => navigate('/mypage')}
        onSelectProduct={(product: Product) => navigate(`/product/${product.id}`)}
      />
    </>
  );
}
