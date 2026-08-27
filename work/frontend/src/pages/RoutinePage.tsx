import { useNavigate } from 'react-router-dom';
import BackgroundSparkles from '../components/BackgroundSparkles';
import RoutineView from '../components/RoutineView';

/** 내 화장품 조합(/routine) — 로그인 상태에서만 마이페이지의 "내 조합 확인하기"나 랜딩의
 * 바로가기로 들어올 수 있으므로 여기서 다시 로그인 여부를 가리지 않는다. 뒤로가기는 항상
 * 마이페이지로 (RoutineView.tsx 상단 주석 참고). */
export default function RoutinePage() {
  const navigate = useNavigate();

  return (
    <>
      <BackgroundSparkles />
      <RoutineView onBack={() => navigate('/mypage')} />
    </>
  );
}
