import type { SkinTypeCount } from '../data/ingredientResult';

interface SkinTypeCountBarsProps {
  skinTypeCounts: SkinTypeCount[];
}

/**
 * "피부 타입별 참고" — 줄글 문장(skin_score_summary) 대신 피부타입별 좋은/유의 성분 개수를
 * 막대바로 보여준다 (app/skin_fit.py compute_skin_type_counts, LLM 아님·DB 집계).
 * 좋음/유의 두 막대 다 같은 스케일(이 제품 안에서 가장 큰 값 기준)로 정규화해서 길이만
 * 보고도 비교가 되게 한다 — 경고 톤은 빨강 대신 --sub(옅은 세이지)로 낮춰서 표현한다
 * (넓은 면적에 accent 한 톤만 쓰는 기존 원칙 유지, .ing-badge--caution과 같은 논리).
 */
export default function SkinTypeCountBars({ skinTypeCounts }: SkinTypeCountBarsProps) {
  if (skinTypeCounts.length === 0) return null;

  const max = Math.max(1, ...skinTypeCounts.flatMap((s) => [s.good_count, s.caution_count]));

  return (
    <div className="skin-type-bar-list">
      {skinTypeCounts.map((s) => (
        <div className="skin-type-bar-row" key={s.skin_type}>
          <span className="skin-type-bar-label">{s.skin_type === '전체' ? '전체 피부타입' : s.skin_type}</span>
          <div className="skin-type-bar-items">
            {s.good_count > 0 && (
              <div className="skin-type-bar-item">
                <div className="skin-type-bar-track">
                  <div
                    className="skin-type-bar-fill skin-type-bar-fill--good"
                    style={{ width: `${(s.good_count / max) * 100}%` }}
                  />
                </div>
                <span className="skin-type-bar-item-label">좋음 {s.good_count}</span>
              </div>
            )}
            {s.caution_count > 0 && (
              <div className="skin-type-bar-item">
                <div className="skin-type-bar-track">
                  <div
                    className="skin-type-bar-fill skin-type-bar-fill--caution"
                    style={{ width: `${(s.caution_count / max) * 100}%` }}
                  />
                </div>
                <span className="skin-type-bar-item-label">유의 {s.caution_count}</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
