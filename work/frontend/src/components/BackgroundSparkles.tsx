import SparkleIcon from '../icons/SparkleIcon';
import BubbleIcon from '../icons/BubbleIcon';
import HeartIcon from '../icons/HeartIcon';
import DropletIcon from '../icons/DropletIcon';

interface SparkleSpec {
  Icon: typeof SparkleIcon;
  top: string;
  left: string;
  size: number; // px
  delay: number; // s
  duration: number; // s
}

// 위치/크기/타이밍을 손으로 흩뿌려서 고정 배치 — 매 렌더마다 값이 바뀌는 Math.random()
// 대신 "의도적으로 배치한 벽지" 느낌을 유지한다. 별·거품 두 가지뿐이면 심심해서
// 하트(귀여움)·물방울(스킨케어 테마)을 더해 네 가지를 골고루 섞었다.
const SPARKLES: SparkleSpec[] = [
  { Icon: SparkleIcon, top: '9%', left: '7%', size: 22, delay: 0, duration: 2.6 },
  { Icon: BubbleIcon, top: '16%', left: '89%', size: 16, delay: 0.8, duration: 3.2 },
  { Icon: HeartIcon, top: '38%', left: '93%', size: 20, delay: 1.6, duration: 2.2 },
  { Icon: DropletIcon, top: '64%', left: '4%', size: 20, delay: 0.4, duration: 3.6 },
  { Icon: SparkleIcon, top: '82%', left: '90%', size: 25, delay: 2.1, duration: 2.8 },
  { Icon: HeartIcon, top: '91%', left: '14%', size: 17, delay: 1.2, duration: 3 },
  { Icon: BubbleIcon, top: '52%', left: '2%', size: 16, delay: 2.6, duration: 2.4 },
  { Icon: SparkleIcon, top: '95%', left: '55%', size: 19, delay: 1.9, duration: 2.5 },
  { Icon: HeartIcon, top: '26%', left: '18%', size: 15, delay: 3.1, duration: 2.9 },
  { Icon: DropletIcon, top: '72%', left: '96%', size: 17, delay: 1.4, duration: 3.1 },
  { Icon: BubbleIcon, top: '46%', left: '97%', size: 12, delay: 2.4, duration: 3.3 },
];

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
