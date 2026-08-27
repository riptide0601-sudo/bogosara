import type { ComponentType } from 'react';

interface SparkleSpec {
  Icon: ComponentType;
  top: string;
  left: string;
  size: number; // px
  delay: number; // s
  duration: number; // s
}

// 별/거품/물방울/하트 전부 뺐다 — 배경 장식 없이 빈 배열.
const SPARKLES: SparkleSpec[] = [];

/**
 * 화면 여백을 채우는 배경 장식 — 오락실 타이틀 화면처럼 떠다니는 픽셀 반짝임(별/거품).
 * 순수 장식이라 aria-hidden + pointer-events:none, 카드/본문보다 항상 뒤(z-index:-1)에
 * 깔린다. 랜딩 화면·결과 화면 양쪽에서 App.tsx가 공용으로 마운트한다.
 */
export default function BackgroundSparkles() {
  return (
    <div className="bg-sparkles" aria-hidden="true">
      {SPARKLES.map(({ Icon, top, left, size, delay, duration }, i) => (
        <span
          key={i}
          className="bg-sparkle"
          style={{
            top,
            left,
            width: size,
            height: size,
            animationDelay: `${delay}s`,
            animationDuration: `${duration}s`,
          }}
        >
          <Icon />
        </span>
      ))}
    </div>
  );
}
