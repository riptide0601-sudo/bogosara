import type { PurposeCount } from '../data/ingredientResult';

interface PurposeCountSectionProps {
  purposeCounts: PurposeCount[];
}

/**
 * "이 성분들, 무슨 일을 하나요?" — 전성분 중 각 배합목적(purpose)에 해당하는 성분이 몇 개인지
 * 카드로 보여준다 (app/purpose_counts.py 참고).
 *
 * 라벨은 원본 purpose_name을 최소 가공(괄호 처리)만 한 것 — "보습" 같은 새 카테고리명을
 * 짓지 않기로 했다(사용자 확인, A안). 그래서 "보습제"와 "피부보습제"처럼 원본 표기가 다르면
 * 서로 합쳐지지 않고 카드가 따로 뜬다.
 */
export default function PurposeCountSection({ purposeCounts }: PurposeCountSectionProps) {
  if (purposeCounts.length === 0) return null;
  const total = purposeCounts[0].total;

  return (
    <div className="result-section">
      <div className="purpose-count-header">
        <h3 className="result-section-title">
          <span className="cursor">▶</span>이 성분들, 무슨 일을 하나요?
        </h3>
        <span className="purpose-count-badge">전성분 {total}개 기준</span>
      </div>
      <div className="purpose-count-grid">
        {purposeCounts.map((pc) => (
          <div className="purpose-count-card" key={pc.label}>
            <p className="purpose-count-label">{pc.label}</p>
            <p className="purpose-count-value">
              {pc.count}
              <span className="purpose-count-value-total"> / {pc.total}</span>
            </p>
            <div className="purpose-count-bar-track">
              <div
                className="purpose-count-bar-fill"
                style={{ width: `${Math.min(100, (pc.count / pc.total) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
