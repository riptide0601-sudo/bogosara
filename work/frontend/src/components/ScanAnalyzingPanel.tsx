import { useEffect, useState } from 'react';
import type { OcrAnalyzeResult } from '../api';

interface ScanAnalyzingPanelProps {
  /** POST /ocr/analyze 응답 — 아직 안 왔으면 null. 오는 순간 아래 성분 칩을 실제 데이터로
   * 몰아서 채운다(장식용 데모 데이터를 쓰지 않는다). */
  result: OcrAnalyzeResult | null;
  /** 성분 계열/순위/피부타입/핵심성분(DB, /ocr/composition)과 LLM 한줄요약/성분구성
   * 설명(/ocr/summarize)까지 전부 준비됐는지 — true가 되면 진행률을 100%로 밀고 "요약 정리"
   * 단계를 완료 처리한다. 결과 화면이 뜨자마자 이미 완성된 내용을 보여주기 위해, ScanOverlay는
   * 이게 true가 될 때까지 페이지 전환을 미룬다(ScanOverlay.tsx runAnalysis 참고) — 그래서
   * 실제로는 result가 온 뒤에도 이 단계가 몇 초 더 걸릴 수 있다(LLM 호출이라 즉시가 아님). */
  ready: boolean;
}

interface StepMeta {
  txt: string;
  sub: string;
  label: string;
}

// 실제 OCR 호출은 한 번의 요청-응답이라 "지금 몇 단계인지"를 서버가 알려주지 않는다.
// 앞의 세 단계는 응답이 오기 전까지 진행률 임계값으로 그럴듯하게 흉내내고(장식),
// 마지막 "요약 정리" 단계만 실제 신호(ready)로 완료 처리한다.
const PRE_STEPS: (StepMeta & { at: number })[] = [
  { txt: '전성분표 글자 인식', sub: 'OCR로 라벨의 텍스트를 읽어요', label: '글자를 인식하는 중', at: 0 },
  { txt: '표준 성분명과 대조', sub: '읽은 성분을 성분 사전과 맞춰봐요', label: '성분 사전과 대조하는 중', at: 35 },
  { txt: '배합목적 분류', sub: '각 성분이 무슨 일을 하는지 나눠요', label: '배합목적을 분류하는 중', at: 68 },
];
const FINAL_STEP: StepMeta = { txt: '요약 정리', sub: '읽기 쉬운 결과로 다듬는 중', label: '요약을 정리하는 중' };
const STEPS: StepMeta[] = [...PRE_STEPS, FINAL_STEP];

// 각 단계에서 진행률이 멈추는 자리 — 다음 실제 신호가 오기 전까지는 이 값을 넘지 않는다.
// OCR 응답 전: 70. 응답 도착~성분 칩 리빌 중: 90. 칩 리빌 끝~ready 대기 중(LLM 호출이라
// 몇 초 걸릴 수 있음): 97. ready===true가 되면 즉시 100.
const PROGRESS_CAP_BEFORE_RESULT = 70;
const PROGRESS_CAP_WHILE_REVEALING = 90;
const PROGRESS_CAP_WHILE_FINALIZING = 97;

// 응답 도착 후 성분 칩을 몰아서 보여주는 시간 — ScanOverlay가 이 값을 가져다 리빌이 끝나기
// 전에 "준비 완료"로 넘어가지 않도록 최소 대기 시간과 묶는다(ScanOverlay.tsx runAnalysis 참고).
export const REVEAL_MS = 1400;

export default function ScanAnalyzingPanel({ result, ready }: ScanAnalyzingPanelProps) {
  const [progress, setProgress] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [revealedCount, setRevealedCount] = useState(0);
  const [chipsDone, setChipsDone] = useState(false);

  // 1) 응답 전 — 앞 세 단계를 진행률 임계값으로 흉내낸다.
  useEffect(() => {
    if (result) return;
    let cur = 0;
    PRE_STEPS.forEach((s, i) => {
      if (progress >= s.at) cur = i;
    });
    setStepIndex(cur);
  }, [progress, result]);

  // 2) 응답 도착 — "요약 정리" 단계로 전환하고, 실제 매칭 결과를 REVEAL_MS 동안 하나씩 몰아서
  // 보여준다. ready가 이미 true(=드물게 매우 빨리 끝난 경우)면 리빌 없이 바로 전부 보여준다.
  useEffect(() => {
    if (!result || ready) {
      if (ready && result) setRevealedCount(result.results.length);
      return;
    }
    setStepIndex(PRE_STEPS.length);

    const items = result.results;
    if (items.length === 0) {
      setChipsDone(true);
      return;
    }
    const tick = Math.max(REVEAL_MS / items.length, 22);
    let i = 0;
    const timer = setInterval(() => {
      i += 1;
      setRevealedCount(i);
      if (i >= items.length) {
        clearInterval(timer);
        setChipsDone(true);
      }
    }, tick);
    return () => clearInterval(timer);
  }, [result, ready]);

  // 3) 진행률을 계속 장식용으로 채워 나간다 — 지금이 어느 단계인지에 따라 멈추는 상한만
  // 다르다. ready가 되기 전까진 100%를 절대 안 찍는다(LLM 응답을 실제로 기다리는 중이라
  // 몇 초가 걸릴 수 있는데, 그 사이 바가 멈춰 보이지 않게 계속 조금씩 움직인다).
  useEffect(() => {
    if (ready) return;
    const cap = !result
      ? PROGRESS_CAP_BEFORE_RESULT
      : !chipsDone
        ? PROGRESS_CAP_WHILE_REVEALING
        : PROGRESS_CAP_WHILE_FINALIZING;
    const timer = setInterval(() => {
      setProgress((p) => Math.min(p + Math.random() * 2.2 + 0.6, cap));
    }, 150);
    return () => clearInterval(timer);
  }, [ready, result, chipsDone]);

  // 4) 전부 준비됨 — 100%로 마무리.
  useEffect(() => {
    if (ready) setProgress(100);
  }, [ready]);

  const total = result?.raw_ingredients.length ?? 0;
  const revealedItems = result ? result.results.slice(0, revealedCount) : [];
  const matchedRevealed = revealedItems.filter((item) => item.ingredient).length;
  const ghostCount = result ? Math.min(5, Math.max(0, 8 - revealedCount)) : 6;

  return (
    <div className="scan-analyzing-panel">
      <span className="scan-analyzing-eyebrow">
        <span className="scan-analyzing-spinner" aria-hidden="true" />
        전성분 분석 중
      </span>

      <h1 className="scan-analyzing-headline">
        촬영한 전성분표에서
        <br />
        표준 성분 <span className="scan-analyzing-num">{matchedRevealed}</span>종을 확인하고 있어요
        <span className="scan-analyzing-caret" aria-hidden="true" />
      </h1>

      <div className="scan-analyzing-progress">
        <div className="scan-analyzing-progress-meta">
          <span className="scan-analyzing-progress-step">{STEPS[stepIndex]?.label}</span>
          <span className="scan-analyzing-progress-pct">{Math.floor(progress)}%</span>
        </div>
        <div className="scan-analyzing-track">
          <div className="scan-analyzing-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="scan-analyzing-steps">
        {STEPS.map((s, i) => (
          <div
            key={s.txt}
            className={`scan-analyzing-step${i === stepIndex && !ready ? ' is-active' : ''}${
              i < stepIndex || ready ? ' is-done' : ''
            }`}
          >
            <span className="scan-analyzing-step-ic" aria-hidden="true">
              {i < stepIndex || ready ? (
                <svg viewBox="0 0 14 14">
                  <path d="M2 7l3 3 7-7" />
                </svg>
              ) : i === stepIndex ? (
                <span className="scan-analyzing-step-dot" />
              ) : null}
            </span>
            <div>
              <div className="scan-analyzing-step-txt">{s.txt}</div>
              <div className="scan-analyzing-step-sub">{s.sub}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="scan-analyzing-chip-zone">
        <p className="scan-analyzing-chip-zone-title">
          인식한 성분{' '}
          <span className="scan-analyzing-chip-count">
            {revealedCount} / {total || '…'}
          </span>
        </p>
        <div className="scan-analyzing-chips">
          {revealedItems.map((item, i) => (
            <span
              key={`${item.label_rank}-${i}`}
              className={`scan-analyzing-chip${item.ingredient ? ' is-matched' : ' is-unmatched'}`}
            >
              {item.matched_text}
            </span>
          ))}
          {Array.from({ length: ghostCount }).map((_, i) => (
            <span
              key={`ghost-${i}`}
              className="scan-analyzing-chip-ghost"
              style={{ width: `${64 + ((i * 37) % 40)}px` }}
            />
          ))}
        </div>
      </div>

      <p className="scan-analyzing-hint">잠시만요 — 성분을 하나하나 확인하고 있어요. 보통 몇 초면 끝나요.</p>
    </div>
  );
}
