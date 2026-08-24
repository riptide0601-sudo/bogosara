/**
 * 배경 장식용 반짝임(별) 픽셀 스프라이트 — 5x5 그리드, 다이아몬드형 트윙클.
 * BackgroundSparkles에서만 쓰는 순수 장식이라 aria-hidden 처리하고 role/label은 두지 않는다.
 */
export default function SparkleIcon() {
  return (
    <svg viewBox="0 0 5 5" aria-hidden="true">
      <g>
      <rect x="2" y="0" width="1" height="1" />
      <rect x="1" y="1" width="1" height="1" />
      <rect x="2" y="1" width="1" height="1" />
      <rect x="3" y="1" width="1" height="1" />
      <rect x="0" y="2" width="1" height="1" />
      <rect x="1" y="2" width="1" height="1" />
      <rect x="2" y="2" width="1" height="1" />
      <rect x="3" y="2" width="1" height="1" />
      <rect x="4" y="2" width="1" height="1" />
      <rect x="1" y="3" width="1" height="1" />
      <rect x="2" y="3" width="1" height="1" />
      <rect x="3" y="3" width="1" height="1" />
      <rect x="2" y="4" width="1" height="1" />
      </g>
    </svg>
  );
}
