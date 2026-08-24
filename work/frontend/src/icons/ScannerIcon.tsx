/**
 * 스캐너 픽셀 스프라이트 — 20x20 그리드, 뷰파인더 브래킷 + 성분표 3x3 그리드 모티프.
 * 그리드는 2x2 셀 + 2유닛 간격으로 짜서 셀 9개가 또렷이 분리돼 보이게 한다
 * (촘촘한 3유닛 셀 + 1유닛 간격이었던 이전 버전은 렌더 크기에서 뭉쳐 보였음).
 * shape-rendering: crispEdges 로 확대해도 흐려지지 않음 (index.css 참고).
 */
export default function ScannerIcon() {
  return (
    <svg className="pixel-icon" viewBox="0 0 20 20" role="img" aria-label="스캐너 아이콘">
      <g>
      {/* 좌상단 브래킷 */}
      <rect x="1" y="1" width="1" height="1" />
      <rect x="1" y="2" width="1" height="1" />
      <rect x="1" y="3" width="1" height="1" />
      <rect x="1" y="4" width="1" height="1" />
      <rect x="1" y="5" width="1" height="1" />
      <rect x="2" y="1" width="1" height="1" />
      <rect x="2" y="2" width="1" height="1" />
      <rect x="2" y="3" width="1" height="1" />
      <rect x="2" y="4" width="1" height="1" />
      <rect x="2" y="5" width="1" height="1" />
      <rect x="3" y="1" width="1" height="1" />
      <rect x="3" y="2" width="1" height="1" />
      <rect x="4" y="1" width="1" height="1" />
      <rect x="4" y="2" width="1" height="1" />
      <rect x="5" y="1" width="1" height="1" />
      <rect x="5" y="2" width="1" height="1" />

      {/* 우상단 브래킷 */}
      <rect x="14" y="1" width="1" height="1" />
      <rect x="14" y="2" width="1" height="1" />
      <rect x="15" y="1" width="1" height="1" />
      <rect x="15" y="2" width="1" height="1" />
      <rect x="16" y="1" width="1" height="1" />
      <rect x="16" y="2" width="1" height="1" />
      <rect x="17" y="1" width="1" height="1" />
      <rect x="17" y="2" width="1" height="1" />
      <rect x="17" y="3" width="1" height="1" />
      <rect x="17" y="4" width="1" height="1" />
      <rect x="17" y="5" width="1" height="1" />
      <rect x="18" y="1" width="1" height="1" />
      <rect x="18" y="2" width="1" height="1" />
      <rect x="18" y="3" width="1" height="1" />
      <rect x="18" y="4" width="1" height="1" />
      <rect x="18" y="5" width="1" height="1" />

      {/* 좌하단 브래킷 */}
      <rect x="1" y="14" width="1" height="1" />
      <rect x="1" y="15" width="1" height="1" />
      <rect x="1" y="16" width="1" height="1" />
      <rect x="1" y="17" width="1" height="1" />
      <rect x="1" y="18" width="1" height="1" />
      <rect x="2" y="14" width="1" height="1" />
      <rect x="2" y="15" width="1" height="1" />
      <rect x="2" y="16" width="1" height="1" />
      <rect x="2" y="17" width="1" height="1" />
      <rect x="2" y="18" width="1" height="1" />
      <rect x="3" y="17" width="1" height="1" />
      <rect x="3" y="18" width="1" height="1" />
      <rect x="4" y="17" width="1" height="1" />
      <rect x="4" y="18" width="1" height="1" />
      <rect x="5" y="17" width="1" height="1" />
      <rect x="5" y="18" width="1" height="1" />

      {/* 우하단 브래킷 */}
      <rect x="14" y="17" width="1" height="1" />
      <rect x="14" y="18" width="1" height="1" />
      <rect x="15" y="17" width="1" height="1" />
      <rect x="15" y="18" width="1" height="1" />
      <rect x="16" y="17" width="1" height="1" />
      <rect x="16" y="18" width="1" height="1" />
      <rect x="17" y="14" width="1" height="1" />
      <rect x="17" y="15" width="1" height="1" />
      <rect x="17" y="16" width="1" height="1" />
      <rect x="17" y="17" width="1" height="1" />
      <rect x="17" y="18" width="1" height="1" />
      <rect x="18" y="14" width="1" height="1" />
      <rect x="18" y="15" width="1" height="1" />
      <rect x="18" y="16" width="1" height="1" />
      <rect x="18" y="17" width="1" height="1" />
      <rect x="18" y="18" width="1" height="1" />

      {/* 성분표 3x3 그리드 — 2x2 셀 9개, 2유닛 간격으로 또렷이 분리 */}
      <rect x="5" y="5" width="1" height="1" />
      <rect x="6" y="5" width="1" height="1" />
      <rect x="9" y="5" width="1" height="1" />
      <rect x="10" y="5" width="1" height="1" />
      <rect x="13" y="5" width="1" height="1" />
      <rect x="14" y="5" width="1" height="1" />
      <rect x="5" y="6" width="1" height="1" />
      <rect x="6" y="6" width="1" height="1" />
      <rect x="9" y="6" width="1" height="1" />
      <rect x="10" y="6" width="1" height="1" />
      <rect x="13" y="6" width="1" height="1" />
      <rect x="14" y="6" width="1" height="1" />
      <rect x="5" y="9" width="1" height="1" />
      <rect x="6" y="9" width="1" height="1" />
      <rect x="9" y="9" width="1" height="1" />
      <rect x="10" y="9" width="1" height="1" />
      <rect x="13" y="9" width="1" height="1" />
      <rect x="14" y="9" width="1" height="1" />
      <rect x="5" y="10" width="1" height="1" />
      <rect x="6" y="10" width="1" height="1" />
      <rect x="9" y="10" width="1" height="1" />
      <rect x="10" y="10" width="1" height="1" />
      <rect x="13" y="10" width="1" height="1" />
      <rect x="14" y="10" width="1" height="1" />
      <rect x="5" y="13" width="1" height="1" />
      <rect x="6" y="13" width="1" height="1" />
      <rect x="9" y="13" width="1" height="1" />
      <rect x="10" y="13" width="1" height="1" />
      <rect x="13" y="13" width="1" height="1" />
      <rect x="14" y="13" width="1" height="1" />
      <rect x="5" y="14" width="1" height="1" />
      <rect x="6" y="14" width="1" height="1" />
      <rect x="9" y="14" width="1" height="1" />
      <rect x="10" y="14" width="1" height="1" />
      <rect x="13" y="14" width="1" height="1" />
      <rect x="14" y="14" width="1" height="1" />
      </g>
    </svg>
  );
}
