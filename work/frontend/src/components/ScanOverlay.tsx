import { useEffect, useRef, useState } from 'react';
import Overlay from './Overlay';

interface ScanOverlayProps {
  open: boolean;
  onClose: () => void;
  /** 캡처 성공 시 호출 — 있으면 OCR 결과 화면(ResultView)으로 이어진다 (App.tsx 참고). */
  onCaptured?: (dataUrl: string) => void;
}

type CameraError = 'denied' | 'not-found' | 'insecure' | 'unknown';

const ERROR_COPY: Record<CameraError, { title: string; body: string; canRetry: boolean }> = {
  denied: {
    title: '카메라 권한이 필요해요',
    body: '브라우저 주소창의 카메라 권한을 허용한 뒤 "다시 시도"를 눌러주세요.',
    canRetry: true,
  },
  'not-found': {
    title: '카메라를 찾을 수 없어요',
    body: '이 기기에서 사용 가능한 카메라가 없는 것 같아요.',
    canRetry: true,
  },
  insecure: {
    title: '안전한 연결이 필요해요',
    body: '카메라는 https 또는 localhost 환경에서만 사용할 수 있어요. file://로 직접 연 경우, 로컬 서버(npm run dev)로 실행한 뒤 다시 열어주세요.',
    canRetry: false,
  },
  unknown: {
    title: '카메라를 시작할 수 없어요',
    body: '잠시 후 "다시 시도"를 눌러주세요.',
    canRetry: true,
  },
};

const CAPTURE_PREVIEW_MS = 1600;

/**
 * 스캐너 클릭 → 그 자리에서 시작되는 실제 웹캠 라이브 스캔 UI.
 * OCR 인식은 아직 없으므로, 캡처한 프레임은 콘솔 로그로만 스텁 처리한다.
 */
export default function ScanOverlay({ open, onClose, onCaptured }: ScanOverlayProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);

  const [streamReady, setStreamReady] = useState(false);
  const [error, setError] = useState<CameraError | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [flash, setFlash] = useState(false);
  const [captureStatus, setCaptureStatus] = useState('');

  /** 카메라 스트림 정지 — 오버레이를 닫을 때 반드시 호출해야 카메라 표시등이 꺼진다. */
  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreamReady(false);
  };

  // 오버레이 열림/닫힘 + 재시도 토큰에 따라 카메라를 켜거나 끈다.
  useEffect(() => {
    if (!open) {
      // 닫힐 때: 스트림 정지 + 캡처 미리보기/에러 상태 초기화 (다음에 열 때 깨끗하게 시작)
      stopStream();
      if (previewTimeoutRef.current !== null) {
        window.clearTimeout(previewTimeoutRef.current);
        previewTimeoutRef.current = null;
      }
      setCapturedImage(null);
      setFlash(false);
      setCaptureStatus('');
      setError(null);
      return;
    }

    let cancelled = false;
    setError(null);
    setStreamReady(false);

    (async () => {
      // 비보안 컨텍스트(https/localhost가 아님)면 getUserMedia 자체가 없거나 즉시 실패한다.
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        if (!cancelled) setError('insecure');
        return;
      }

      try {
        // 후면 카메라를 우선 요청 (ideal이므로 후면 카메라가 없는 데스크톱 등에서는
        // 자동으로 사용 가능한 기본 카메라로 대체된다)
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
    };
  }, [open, retryToken]);

  // 언마운트 시 안전망 — 혹시 모를 경우에도 카메라는 반드시 꺼둔다.
  useEffect(() => stopStream, []);

  /** 현재 영상 프레임을 캔버스에 캡처 — OCR 연동 전까지는 미리보기 + console.log 스텁. */
  const handleCapture = () => {
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

    console.log('[보고사라][스캔] 캡처 완료:', {
      width,
      height,
      dataUrlPreview: `${dataUrl.slice(0, 40)}…`,
    });

    setFlash(true);
    window.setTimeout(() => setFlash(false), 220);

    if (onCaptured) {
      // OCR 연동 지점 (data/ingredientResult.ts의 loadIngredientResult 참고) —
      // App.tsx가 이 시점에 오버레이를 닫고 결과 화면(로딩→성공/실패)으로 넘어간다.
      onCaptured(dataUrl);
      return;
    }

    // onCaptured가 없을 때(App에 연결 안 된 단독 사용)를 위한 폴백: 캡처 미리보기만 잠깐 보여준다.
    setCapturedImage(dataUrl);
    setCaptureStatus('촬영됨 ✓ (OCR 인식은 추후 연동 예정 · 콘솔 로그 참고)');
    if (previewTimeoutRef.current !== null) window.clearTimeout(previewTimeoutRef.current);
    previewTimeoutRef.current = window.setTimeout(() => {
      setCapturedImage(null);
      setCaptureStatus('');
    }, CAPTURE_PREVIEW_MS);
  };

  const errorCopy = error ? ERROR_COPY[error] : null;

  return (
    <Overlay id="overlay-scan" titleId="scan-title" title="전성분 스캔" open={open} onClose={onClose}>
      <div className="scan-frame">
        {/* 실제 웹캠 라이브 영상 */}
        <video
          ref={videoRef}
          className="scan-video"
          autoPlay
          playsInline
          muted
          style={{ opacity: streamReady && !error ? 1 : 0 }}
        />

        {/* 카메라 준비 중 (권한 요청 대기 포함) */}
        {!streamReady && !error && <p className="scan-loading">카메라 준비 중...</p>}

        {/* 예외 처리: 권한 거부 / 카메라 없음 / 비보안 컨텍스트 — 픽셀 스타일 안내 박스 */}
        {errorCopy && (
          <div className="scan-error-box" role="alert">
            <p className="scan-error-title">{errorCopy.title}</p>
            <p className="scan-error-body">{errorCopy.body}</p>
            {errorCopy.canRetry && (
              <button type="button" className="btn-primary" onClick={() => setRetryToken((n) => n + 1)}>
                다시 시도
              </button>
            )}
          </div>
        )}

        {/* 뷰파인더 브래킷 + 위아래로 움직이는 스캔 라인 (영상 위에 오버레이) */}
        {streamReady && !error && (
          <>
            <span className="scan-corner tl" />
            <span className="scan-corner tr" />
            <span className="scan-corner bl" />
            <span className="scan-corner br" />
            <span className="scan-line" />
            <p className="scan-hint">전성분표를 프레임 안에 맞춰주세요</p>
          </>
        )}

        {/* 촬영 직후 잠깐 보여주는 캡처 미리보기 */}
        {capturedImage && <img className="scan-captured-preview" src={capturedImage} alt="캡처 미리보기" />}

        {/* 셔터 플래시 효과 */}
        {flash && <div className="scan-flash" aria-hidden="true" />}

        {/* 캡처용 캔버스 (화면에는 보이지 않음) */}
        <canvas ref={canvasRef} className="scan-canvas" />
      </div>

      <div className="scan-actions">
        <button type="button" className="btn-primary" onClick={handleCapture} disabled={!streamReady || !!error}>
          촬영하기
        </button>
      </div>
      <p className="scan-status" role="status">
        {captureStatus}
      </p>
      <p className="scan-note">※ 카메라 스캔 기능은 https 또는 localhost 환경에서만 동작합니다.</p>
    </Overlay>
  );
}
