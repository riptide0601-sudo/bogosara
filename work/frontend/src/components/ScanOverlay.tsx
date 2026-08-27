import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface ScanOverlayProps {
  onClose: () => void;
}

type CameraError = 'denied' | 'not-found' | 'insecure' | 'unknown';

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
 * 촬영하면 캡처한 프레임을 들고 /scan-result로 이동한다 (OCR 인식은 ScanResultPage/백엔드 쪽 몫).
 */
export function ScanOverlay({ onClose }: ScanOverlayProps) {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [streamReady, setStreamReady] = useState(false);
  const [error, setError] = useState<CameraError | null>(null);
  const [retryToken, setRetryToken] = useState(0);

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
    navigate('/scan-result', { state: { image: dataUrl } });
    onClose();
  };

  const errorCopy = error ? ERROR_COPY[error] : null;

  return (
    <div className="scan-page">
      <button type="button" className="scan-page__close" onClick={onClose} aria-label="닫기">
        ×
      </button>

      <video
        ref={videoRef}
        className="scan-page__video"
        autoPlay
        playsInline
        muted
        style={{ opacity: streamReady && !error ? 1 : 0 }}
      />

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
      ) : (
        <>
          <div className="scan-page__frame">
            <span className="scan-corner tl" />
            <span className="scan-corner tr" />
            <span className="scan-corner bl" />
            <span className="scan-corner br" />
            <span className="scan-line" />
          </div>
          <p className="scan-page__hint">전성분표를 프레임 안에 맞춰주세요</p>
          <button
            type="button"
            className="scan-page__shutter"
            onClick={handleCapture}
            disabled={!streamReady}
            aria-label="촬영하기"
          />
        </>
      )}

      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
}
