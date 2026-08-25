import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import * as authApi from '../api/auth';
import { clearToken, getToken, setToken } from '../api/client';
import { getMe } from '../api/users';
import type { UserRead } from '../api/types';

interface AuthContextValue {
  user: UserRead | null;
  /** 새로고침 직후, 저장된 토큰으로 /users/me를 조회하는 동안 true — 이 사이엔 로그인
   * 여부를 아직 몰라서 App.tsx가 로그인/마이페이지 어느 쪽도 확정해서 그리면 안 된다. */
  initializing: boolean;
  setUser: (user: UserRead) => void;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, nickname: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(null);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setInitializing(false);
      return;
    }
    getMe()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setInitializing(false));
  }, []);

  const login = async (email: string, password: string) => {
    const { access_token, user: loggedInUser } = await authApi.login(email, password);
    setToken(access_token);
    setUser(loggedInUser);
  };

  const signup = async (email: string, nickname: string, password: string) => {
    const { access_token, user: newUser } = await authApi.signup(email, nickname, password);
    setToken(access_token);
    setUser(newUser);
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, initializing, setUser, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth는 AuthProvider 안에서만 쓸 수 있습니다.');
  return ctx;
}
