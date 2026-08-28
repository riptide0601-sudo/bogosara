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
      <p className="result-section-desc">
        전성분 중 각 배합목적에 해당하는 성분이 몇 개인지 보여드려요.
      </p>
      <div className="purpose-count-grid">
        {purposeCounts.map((pc) => (
          <div className="purpose-count-card" key={pc.label}>
            <div className="purpose-count-label-row">
              <p className="purpose-count-label">{pc.label}</p>
              {/* 배합목적이 일반 단어가 아니라 뜻이 바로 안 와닿을 수 있어서, DB에 뜻풀이
                  (purpose.description)가 있는 라벨만 느낌표 아이콘을 붙여 호버 시 보여준다 —
                  없는 라벨은 지어내지 않고 그냥 아이콘 자체를 생략한다. label 바깥(형제)에
                  둬야 label의 overflow:hidden(말줄임)에 툴팁이 같이 잘리지 않는다.
                  stopPropagation — 이 카드가 결과 카드(ResultCard) 앞면 안에 있고, 그
                  앞면 자체가 클릭하면 전성분 뒷면으로 뒤집히는 큰 클릭 영역이라, 없으면
                  터치 기기에서 이 아이콘을 탭할 때 카드가 같이 뒤집혀 버린다. */}
              {pc.description && (
                <span
                  className="purpose-count-info"
                  tabIndex={0}
                  onClick={(e) => e.stopPropagation()}
                >
                  !<span className="purpose-count-tooltip">{pc.description}</span>
                </span>
              )}
            </div>
            {/* "N/전체"가 이 카드의 핵심 수치라 크고 진하게, label은 반대로 낮춘 톤 —
                강약 대비를 위해서다(purpose-count-label은 위에서 이미 옅은 톤). */}
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
