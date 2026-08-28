import { useNavigate } from 'react-router-dom';
import BackgroundSparkles from '../components/BackgroundSparkles';
import WalkingMascot from '../components/WalkingMascot';
import MyPageView from '../components/MyPageView';
import LoginView from '../components/LoginView';
import { useAuth } from '../context/AuthContext';
import CosmeticMascotIcon from '../icons/CosmeticMascotIcon';
import CreamJarIcon from '../icons/CreamJarIcon';
import CushionIcon from '../icons/CushionIcon';
import type { SavedResult } from '../data/myPage';
import type { RoutineHistoryRead } from '../api/types';

/** 걸어다니는 캐릭터 행렬 — 화장품 병(리더) 뒤로 수분크림통·쿠션이 쫄래쫄래 따라간다. */
const WALKING_MASCOTS = [
  { Icon: CosmeticMascotIcon, width: 34, height: 45, bottom: 6, walkDuration: 13, walkDelay: 0, bobDuration: 0.5, restLeft: 20 },
  { Icon: CreamJarIcon, width: 26, height: 24, bottom: 6, walkDuration: 13, walkDelay: 0.35, bobDuration: 0.42, restLeft: 58 },
  { Icon: CushionIcon, width: 20, height: 22, bottom: 6, walkDuration: 13, walkDelay: 0.65, bobDuration: 0.36, restLeft: 88 },
];

/** 마이페이지(/mypage) — 로그인 상태면 MyPageView, 아니면 LoginView. initializing 동안은
 * (새로고침 직후 저장된 토큰으로 /users/me 조회 중) 로그인 여부를 아직 몰라서 둘 다 안 그린다. */
export default function MyPagePage() {
  const { user, initializing } = useAuth();
  const navigate = useNavigate();

  const handleSelectSavedResult = (result: SavedResult) => {
    navigate(`/product/${result.id}`);
  };

  const handleOpenRoutineHistory = (entry: RoutineHistoryRead) => {
    navigate('/routine', { state: { historyEntry: entry } });
  };

  return (
    <>
      <BackgroundSparkles />
      {WALKING_MASCOTS.map((mascot, i) => (
        <WalkingMascot key={i} {...mascot} />
      ))}
      {!initializing &&
        (user ? (
          <MyPageView
            onBack={() => navigate('/')}
            onSelectSavedResult={handleSelectSavedResult}
            onOpenRoutine={() => navigate('/routine')}
            onOpenRoutineHistory={handleOpenRoutineHistory}
          />
        ) : (
          <LoginView onBack={() => navigate('/')} onSuccess={() => {}} />
        ))}
    </>
  );
}
