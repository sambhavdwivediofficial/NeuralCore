// frontend/context/AuthContext.jsx

'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import * as authService from '@/services/auth';
import { ROUTES } from '@/lib/routes';
import { AUTH_COOKIE_NAME } from '@/lib/constants';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [mfaPending, setMfaPending] = useState(null);
  const loadedRef = useRef(false);

  const hasCookie = () =>
    typeof document !== 'undefined' &&
    document.cookie.split(';').some((c) => c.trim().startsWith(`${AUTH_COOKIE_NAME}=`));

  const loadUser = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await authService.getCurrentUser();
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    if (hasCookie()) {
      loadUser();
    } else {
      setIsLoading(false);
    }
  }, [loadUser]);

  const signIn = useCallback(async (credentials) => {
    const data = await authService.login(credentials);
    if (data.mfa_required) {
      setMfaPending(data.challenge_token);
      return { mfa_required: true };
    }
    setUser(data.user ?? data);
    return data;
  }, []);

  const completeMfa = useCallback(async (code) => {
    if (!mfaPending) throw new Error('No MFA challenge active');
    const data = await authService.completeMfaChallenge(mfaPending, code);
    setMfaPending(null);
    setUser(data.user ?? data);
    return data;
  }, [mfaPending]);

  const signOut = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setMfaPending(null);
      router.push(ROUTES.LOGIN);
    }
  }, [router]);

  const updateUser = useCallback((partial) => {
    setUser((prev) => (prev ? { ...prev, ...partial } : prev));
  }, []);

  const value = useMemo(() => ({
    user,
    isAuthenticated: Boolean(user),
    isLoading,
    mfaPending: Boolean(mfaPending),
    signIn,
    completeMfa,
    signOut,
    updateUser,
    refresh: loadUser,
  }), [user, isLoading, mfaPending, signIn, completeMfa, signOut, updateUser, loadUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider');
  return ctx;
}
