import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzeOcrImage } from '../api';
import Overlay from './Overlay';

interface ScanOverlayProps {
  onClose: () => void;
}

/** live: 라이브 뷰파인더. analyzing: 촬영 직후 OCR 응답을 기다리는 중(정지 프레임 + 스캔
 * 모션). failed: OCR은 끝났지만 아무 성분도 못 읽어서 실패 모달을 띄운 상태. */
type ScanPhase = 'live' | 'analyzing' | 'failed';

type CameraError = 'denied' | 'not-found' | 'insecure' | 'unknown';

/** OCR 응답이 실제로는 순식간(수백ms)에 오거나 실패해도, "스캐너가 사진을 훑고 판단하는"
 * 모먼트가 최소 이만큼은 눈에 보이게 강제한다 — 안 그러면 analyzing 단계가 깜빡이듯 지나가서
 * 뭘 하고 있었는지 인지가 안 된다. 스캔 라인(App.css .scan-line--analyzing, 왕복 1.4s)이
 * 최소 한 번 이상 오갈 시간. */
const MIN_ANALYZING_MS = 2000;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const ERROR_COPY: Record<CameraError, { title: string; body: string; canRetry: boolean }> = {
  denied: {
    title: '카메라 권한이 필요해요',
    body: '브라우저 주소창의 카메라 권한을 허용한 뒤 다시 시도해주세요.',
    canRetry: true,
  },
  'not-found': {
    title: '카메라를 찾을 수 없어요',
    body: '이 기기에서 사용 가능한 카메라가 없는 것 같아요.',
    canRetry: true,
  },
  insecure: {
    title: '안전한 연결이 필요해요',
    body: '카메라는 https 또는 localhost 환경에서만 사용할 수 있어요.',
    canRetry: false,
  },
  unknown: {
    title: '카메라를 시작할 수 없어요',
    body: '잠시 후 다시 시도해주세요.',
    canRetry: true,
  },
};

/**
 * 히어로 오른쪽(SCAN) 클릭 → 뜨는 실제 웹캠 라이브 스캔 화면.
 * 촬영 버튼을 누르면 바로 다음 페이지로 넘기지 않고, 그 자리에서 POST /ocr/analyze로 실제
 * OCR을 돌려 성분을 하나라도 읽었는지 확인한다(analyzing 단계 — 정지 프레임 위에 스캔 모션).
 * 인식에 성공해야만 /scan-result로 넘어가고, 실패하면 이 화면에 실패 모달을 띄운다(failed
 * 단계) — "찍자마자 무조건 다음 페이지"가 아니라 인식 성공이 곧 다음 페이지로 가는 조건이다.
 *
 * 카메라 없이도 쓸 수 있게 PC 파일 업로드도 지원한다 — 화면 전체가 드롭 영역이라 탐색기에서
 * 이미지를 끌어다 놓거나, "PC에서 사진 올리기" 버튼으로 파일 선택창을 열 수 있다. 둘 다
 * runAnalysis로 들어가 카메라 촬영과 동일한 OCR 흐름을 탄다.
 */
export function ScanOverlay({ onClose }: ScanOverlayProps) {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [streamReady, setStreamReady] = useState(false);
  const [error, setError] = useState<CameraError | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  const [phase, setPhase] = useState<ScanPhase>('live');
  const [capturedDataUrl, setCapturedDataUrl] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreamReady(false);
  };

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setStreamReady(false);

    (async () => {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        if (!cancelled) setError('insecure');
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' } },
          audio: false,
        });

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setStreamReady(true);
      } catch (err) {
        if (cancelled) return;
        const name = err instanceof DOMException ? err.name : '';
        if (name === 'NotAllowedError' || name === 'PermissionDeniedError') setError('denied');
        else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') setError('not-found');
        else {
          setError('unknown');
          console.error('[보고사라][스캔] 카메라 시작 실패:', err);
        }
      }
    })();

    return () => {
      cancelled = true;
      stopStream();
    };
  }, [retryToken]);

  // 언마운트 시(뒤로가기, X 버튼 등) 아직 안 끝난 OCR 요청은 그냥 버려둬도 결과를 어차피 안
  // 쓰지만, 굳이 응답을 기다릴 이유가 없어 취소한다.
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  // 카메라 촬영과 PC 업로드가 이 뒤부터는 같은 경로를 탄다 — 둘 다 "이미지 하나 + 그 데이터
  // URL"을 만들어서 여기 넘기기만 하면 된다(analyzing 표시 → OCR 호출 → 최소 대기 →
  // 성공/실패 분기는 출처와 무관하게 동일하다).
  const runAnalysis = async (blob: Blob | null, dataUrl: string) => {
    setCapturedDataUrl(dataUrl);
    setPhase('analyzing');
    const analyzingStartedAt = Date.now();

    const controller = new AbortController();
    abortRef.current = controller;

    let outcome: { ok: true; result: Awaited<ReturnType<typeof analyzeOcrImage>> } | { ok: false } | 'aborted';
    if (!blob) {
      outcome = { ok: false };
    } else {
      try {
        const result = await analyzeOcrImage(blob, controller.signal);
        outcome = { ok: true, result };
      } catch (err) {
        if (controller.signal.aborted) {
          outcome = 'aborted';
        } else {
          console.error('[보고사라][스캔] OCR 분석 실패:', err);
          outcome = { ok: false };
        }
      }
    }
    if (outcome === 'aborted') return; // 그 사이 사용자가 닫았거나 언마운트됨 — 무시.

    // OCR 응답이 순식간에 와도 "스캐너가 사진을 훑고 판단하는" 모먼트가 최소한은 보이도록
    // 남은 시간만큼 더 기다린다 — 실제로 오래 걸렸다면 이미 충분히 지났으니 더 안 기다린다.
    await wait(Math.max(0, MIN_ANALYZING_MS - (Date.now() - analyzingStartedAt)));
    if (controller.signal.aborted) return; // 대기하는 사이 닫혔을 수도 있다.

    // raw_ingredients가 비어 있으면 OCR 자체는 응답했지만 글자를 하나도 못 읽었다는 뜻 —
    // 이 경우도 사용자 입장에선 "인식 실패"다.
    if (outcome.ok && outcome.result.raw_ingredients.length > 0) {
      navigate('/scan-result', { state: { image: dataUrl, ocr: outcome.result } });
      onClose();
    } else {
      setPhase('failed');
    }
  };

  const handleCapture = async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !streamReady) return;

    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) return;

    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, width, height);

    const dataUrl = canvas.toDataURL('image/png');
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
    await runAnalysis(blob, dataUrl);
  };

  /** PC에서 고른/드롭한 이미지 파일 — "업로드하기" 버튼과 드래그 앤 드롭이 공유한다. */
  const handleFileSelected = (file: File) => {
    if (phase !== 'live' || !file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') runAnalysis(file, reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    if (phase !== 'live') return;
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (phase !== 'live') return;
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileSelected(file);
  };

  const handleRetry = () => {
    setPhase('live');
    setCapturedDataUrl(null);
  };

  const handleClose = () => {
    abortRef.current?.abort();
    onClose();
  };

  const errorCopy = error ? ERROR_COPY[error] : null;

  return (
    <div
      className="scan-page"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <button type="button" className="scan-page__close" onClick={handleClose} aria-label="닫기">
        ×
      </button>

      <video
        ref={videoRef}
        className="scan-page__video"
        autoPlay
        playsInline
        muted
        style={{ opacity: phase === 'live' && streamReady && !error ? 1 : 0 }}
      />

      {/* PC에서 파일을 끌어다 화면 위로 올렸을 때 — "여기에 놓으면 된다"는 걸 확실히 보여준다. */}
      {dragActive && (
        <div className="scan-page__drop-hint" aria-hidden="true">
          <p>여기에 놓으면 업로드돼요</p>
        </div>
      )}

      {errorCopy ? (
        <p className={`scan-page__status${error ? ' scan-page__status--error' : ''}`} role="alert">
          {errorCopy.title} · {errorCopy.body}
          {errorCopy.canRetry && (
            <>
              {' '}
              <button type="button" onClick={() => setRetryToken((n) => n + 1)}>
                다시 시도
              </button>
            </>
          )}
        </p>
      ) : phase === 'live' ? (
        <>
          <div className="scan-page__frame">
            <span className="scan-corner tl" />
            <span className="scan-corner tr" />
            <span className="scan-corner bl" />
            <span className="scan-corner br" />
            <span className="scan-line" />
          </div>
          <p className="scan-page__hint">전성분표를 프레임 안에 맞춰주세요</p>
          <div className="scan-page__actions">
            <button
              type="button"
              className="scan-page__shutter"
              onClick={handleCapture}
              disabled={!streamReady}
              aria-label="촬영하기"
            />
            <button
              type="button"
              className="scan-page__upload-btn"
              onClick={() => fileInputRef.current?.click()}
            >
              사진 업로드
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="scan-page__file-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileSelected(file);
              e.target.value = ''; // 같은 파일을 다시 골라도 onChange가 또 뜨도록 초기화
            }}
          />
        </>
      ) : phase === 'analyzing' ? (
        <>
          {/* 촬영/업로드한 사진을 화면 전체가 아니라 뷰파인더 프레임 "안에" 담아 보여준다 —
              라이브 카메라 미리보기와 달리 이 사진은 프레임 비율(3:4)에 맞춰 잘려서 프레임
              테두리 안에서만 보인다(사진 원본 비율이 화면 비율과 달라도 프레임 밖으로 안 삐져나옴). */}
          <div className="scan-page__frame scan-page__frame--analyzing">
            {capturedDataUrl && (
              <img className="scan-page__captured" src={capturedDataUrl} alt="촬영하거나 업로드한 전성분표 사진" />
            )}
            <span className="scan-corner tl" />
            <span className="scan-corner tr" />
            <span className="scan-corner bl" />
            <span className="scan-corner br" />
            <span className="scan-line scan-line--analyzing" />
          </div>
          <p className="scan-page__hint">전성분표를 읽고 있어요…</p>
        </>
      ) : phase === 'failed' ? (
        <div className="scan-page__frame">
          {capturedDataUrl && (
            <img className="scan-page__captured" src={capturedDataUrl} alt="촬영하거나 업로드한 전성분표 사진" />
          )}
        </div>
      ) : null}

      <Overlay
        id="scan-fail-overlay"
        titleId="scan-fail-title"
        title="인식하지 못했어요"
        open={phase === 'failed'}
        onClose={handleRetry}
      >
        <p className="overlay-message">
          전성분표 글자를 읽지 못했어요. 밝은 곳에서 표가 프레임 가득 보이게 다시 찍어주세요.
        </p>
        <button type="button" className="btn-primary" onClick={handleRetry}>
          다시 촬영하기
        </button>
      </Overlay>

      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
}
