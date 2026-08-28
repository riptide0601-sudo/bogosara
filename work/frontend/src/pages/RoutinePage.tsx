import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import BackgroundSparkles from '../components/BackgroundSparkles';
import RoutineView from '../components/RoutineView';
import { getRoutineHistoryAnalysis } from '../api/routine';
import type { RoutineAnalysis, RoutineHistoryRead } from '../api/types';

interface RoutineRouteState {
  historyEntry?: RoutineHistoryRead;
}

/** 내 화장품 조합(/routine) — 로그인 상태에서만 마이페이지의 "내 조합 확인하기"나 랜딩의
 * 바로가기로 들어올 수 있으므로 여기서 다시 로그인 여부를 가리지 않는다. "뒤로가기"는
 * 브라우저 히스토리로 돌아가서, 어느 쪽에서 들어왔든 원래 있던 화면으로 자연스럽게 나간다.
 *
 * 마이페이지의 "조합 기록" 카드를 눌러 들어온 경우 router state로 historyEntry가 같이
 * 넘어온다(ScanResultPage의 image state와 같은 패턴) — 그 저장된 조합을 다시 분석해서
 * RoutineView에 넘겨준다. */
export default function RoutinePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const historyEntry = (location.state as RoutineRouteState | null)?.historyEntry ?? null;

  const [historyAnalysis, setHistoryAnalysis] = useState<RoutineAnalysis | null>(null);

  useEffect(() => {
    if (!historyEntry) return;
    let cancelled = false;
    getRoutineHistoryAnalysis(historyEntry.history_id)
      .then((result) => {
        if (!cancelled) setHistoryAnalysis(result);
      })
      .catch((err) => {
        console.error('[보고사라][내 조합] 기록 분석 조회 실패', err);
      });
    return () => {
      cancelled = true;
    };
  }, [historyEntry]);

  return (
    <>
      <BackgroundSparkles />
      <RoutineView
        onBack={() => navigate(-1)}
        onSelectProduct={(productId) => navigate(`/product/${productId}`)}
        historyEntry={historyEntry}
        historyAnalysis={historyAnalysis}
      />
    </>
  );
}
