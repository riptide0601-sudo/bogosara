import { useState } from 'react';
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
 *
 * 피부타입마다 막대가 1~2개(유의 0개면 좋음만)라 줄 수가 들쭉날쭉해서 어떤 막대가 어떤
 * 피부타입 것인지 헷갈린다는 피드백으로, 피부타입 하나당 테두리 있는 카드로 묶었다.
 * 막대를 누르면 그 근거가 된 실제 성분명을 바로 펼쳐 보여준다(good_ingredients/
 * caution_ingredients — count와 같은 소스, LLM 아님).
 */
export default function SkinTypeCountBars({ skinTypeCounts }: SkinTypeCountBarsProps) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  if (skinTypeCounts.length === 0) return null;

  const max = Math.max(1, ...skinTypeCounts.flatMap((s) => [s.good_count, s.caution_count]));

  const toggle = (key: string) => setOpenKey((cur) => (cur === key ? null : key));

  return (
    <div className="skin-type-bar-list">
      {skinTypeCounts.map((s) => (
        <div className="skin-type-bar-row" key={s.skin_type}>
          <span className="skin-type-bar-label">{s.skin_type}</span>
          <div className="skin-type-bar-items">
            {s.good_count > 0 && (
              <SkinTypeBarItem
                toneClass="skin-type-bar-fill--good"
                itemLabel={`좋음 ${s.good_count}`}
                width={(s.good_count / max) * 100}
                ingredients={s.good_ingredients}
                open={openKey === `${s.skin_type}-good`}
                onToggle={() => toggle(`${s.skin_type}-good`)}
              />
            )}
            {s.caution_count > 0 && (
              <SkinTypeBarItem
                toneClass="skin-type-bar-fill--caution"
                itemLabel={`유의 ${s.caution_count}`}
                width={(s.caution_count / max) * 100}
                ingredients={s.caution_ingredients}
                open={openKey === `${s.skin_type}-caution`}
                onToggle={() => toggle(`${s.skin_type}-caution`)}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

interface SkinTypeBarItemProps {
  toneClass: string;
  itemLabel: string;
  width: number;
  ingredients: string[];
  open: boolean;
  onToggle: () => void;
}

function SkinTypeBarItem({ toneClass, itemLabel, width, ingredients, open, onToggle }: SkinTypeBarItemProps) {
  return (
    <div className="skin-type-bar-item">
      <button
        type="button"
        className="skin-type-bar-item-btn"
        onClick={(e) => {
          // 이 카드 전체가 결과 카드(ResultCard) 앞면 안에 있고, 그 앞면 자체가 클릭하면
          // 전성분 뒷면으로 뒤집히는 큰 클릭 영역이다 — stopPropagation 없으면 여기 클릭이
          // 그 상위 핸들러까지 올라가서 카드가 같이 뒤집혀 버린다.
          e.stopPropagation();
          onToggle();
        }}
        aria-expanded={open}
      >
        <div className="skin-type-bar-track">
          <div className={`skin-type-bar-fill ${toneClass}`} style={{ width: `${width}%` }} />
        </div>
        <span className="skin-type-bar-item-label">{itemLabel}</span>
      </button>
      {open && ingredients.length > 0 && (
        <ul className="skin-type-bar-ingredients">
          {ingredients.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
