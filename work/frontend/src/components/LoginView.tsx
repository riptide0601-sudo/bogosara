import { useState, type FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../api/client';
import '../LoginView.css';

interface LoginViewProps {
  onBack: () => void;
  /** 로그인/회원가입 성공 시 App.tsx가 원래 가려던 화면(마이페이지)으로 이어준다. */
  onSuccess: () => void;
}

type Mode = 'login' | 'signup';

const MIN_PASSWORD_LENGTH = 8;

/**
 * 로그인/회원가입 화면 — 이메일 + 비밀번호(+ 회원가입 시 닉네임·비밀번호 확인)를 받는다
 * (app/schemas/user.py — 비밀번호는 8자 이상, bcrypt로 해시해서 저장한다). 오버레이가
 * 아니라 MyPageView/ResultView와 같은 "페이지 전체 전환" 패턴을 쓴다 — 뒤로가기 바
 * (.result-topbar/.result-back-btn)를 그대로 재사용한다.
 */
export default function LoginView({ onBack, onSuccess }: LoginViewProps) {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setError(null);

    if (mode === 'signup') {
      if (password.length < MIN_PASSWORD_LENGTH) {
        setError(`비밀번호는 ${MIN_PASSWORD_LENGTH}자 이상이어야 해요.`);
        return;
      }
      if (password !== confirmPassword) {
        setError('비밀번호가 서로 일치하지 않아요.');
        return;
      }
    }

    setSubmitting(true);
    try {
      if (mode === 'signup') {
        await signup(email.trim(), nickname.trim(), password);
      } else {
        await login(email.trim(), password);
      }
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError('이미 가입된 이메일이에요. 아래에서 로그인으로 전환해주세요.');
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('서버에 연결하지 못했어요. 잠시 후 다시 시도해주세요.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = () => {
    setMode((m) => (m === 'login' ? 'signup' : 'login'));
    setPassword('');
    setConfirmPassword('');
    setError(null);
  };

  return (
    <div className="login-view">
      <header className="result-topbar">
        <button type="button" className="result-back-btn" onClick={onBack}>
          <span className="cursor">◀</span>홈으로
        </button>
      </header>

      <h1 className="mypage-title">
        <span className="cursor">▶</span>
        {mode === 'login' ? '로그인' : '회원가입'}
      </h1>

      <div className="login-card">
        <p className="login-card-desc">
          {mode === 'login' ? '이메일과 비밀번호로 로그인해요.' : '이메일과 비밀번호로 간편하게 가입해요.'}
        </p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="login-field">
            <span className="login-field-label">이메일</span>
            <input
              type="email"
              className="search-input login-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
          </label>

          {mode === 'signup' && (
            <label className="login-field">
              <span className="login-field-label">닉네임</span>
              <input
                type="text"
                className="search-input login-input"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="마이페이지에 표시될 이름"
                required
                autoComplete="nickname"
              />
            </label>
          )}

          <label className="login-field">
            <span className="login-field-label">비밀번호</span>
            <input
              type="password"
              className="search-input login-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === 'signup' ? `${MIN_PASSWORD_LENGTH}자 이상` : '비밀번호'}
              required
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
            />
          </label>

          {mode === 'signup' && (
            <label className="login-field">
              <span className="login-field-label">비밀번호 확인</span>
              <input
                type="password"
                className="search-input login-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="비밀번호를 한 번 더 입력해주세요"
                required
                autoComplete="new-password"
              />
            </label>
          )}

          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="btn-primary login-submit" disabled={submitting}>
            {submitting ? (
              <>
                <span className="spinner" aria-hidden="true" />
                처리 중...
              </>
            ) : mode === 'login' ? (
              '로그인'
            ) : (
              '회원가입'
            )}
          </button>
        </form>

        <button type="button" className="mypage-ghost-btn login-switch" onClick={switchMode}>
          {mode === 'login' ? '계정이 없으신가요? 회원가입' : '이미 계정이 있으신가요? 로그인'}
        </button>
      </div>
    </div>
  );
}
