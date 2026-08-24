import type { ComponentType, CSSProperties } from 'react';

interface WalkingMascotProps {
  Icon: ComponentType;
  width: number;
  height: number;
  /** 화면 바닥에서부터의 거리(px) — 셋 다 같은 값을 주면 한 줄로 나란히 걷는다 */
  bottom: number;
  /** 좌→우 이동 한 바퀴 걸리는 시간(초). 리더와 같은 값을 줘야 대형이 안 벌어진다 */
  walkDuration: number;
  /** 이 값만큼 늦게 출발 — 리더보다 delay를 크게 주면 "뒤따라오는" 효과가 난다 */
  walkDelay: number;
  /** 통통 튀는 바운스 주기(초) — 작은 캐릭터일수록 짧게 줘서 종종걸음 느낌을 낸다 */
  bobDuration: number;
  /** prefers-reduced-motion일 때 멈춰 서 있을 자리(px) — 셋이 겹치지 않게 각자 다르게 준다 */
  restLeft: number;
}

/**
 * 화면 맨 아래를 좌→우로 걸어다니는 캐릭터 한 마리.
 * 실제 걷기 프레임(다리 교차)은 없고, 대신 이동(느린 좌우 translate)과 통통 튀는
 * 바운스(빠른 rotate+translateY)를 겹쳐서 "걷는" 느낌을 낸다 — 각각 다른 요소에 걸어야
 * transform이 서로 덮어쓰지 않는다 (App.css .walking-mascot 주석 참고).
 * 여러 마리를 walkDelay만 다르게 줘서 같이 띄우면 뒤따라오는 행렬처럼 보인다.
 * 순수 장식이라 aria-hidden + pointer-events:none.
 */
export default function WalkingMascot({ Icon, width, height, bottom, walkDuration, walkDelay, bobDuration, restLeft }: WalkingMascotProps) {
  return (
    <div
      className="walking-mascot"
      aria-hidden="true"
      style={{
        bottom,
        animationDuration: `${walkDuration}s`,
        animationDelay: `${walkDelay}s`,
        // prefers-reduced-motion용 — App.css에서 var(--rest-left)로 참조한다
        '--rest-left': `${restLeft}px`,
      } as CSSProperties}
    >
      <div
        className="walking-mascot-body"
        style={{ width, height, animationDuration: `${bobDuration}s` }}
      >
        <Icon />
      </div>
    </div>
  );
}
