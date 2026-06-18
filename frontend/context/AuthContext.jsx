// context/AuthContext.jsx

'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import * as authService from '@/services/auth';
import { ROUTES } from '@/lib/routes';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadUser = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await authService.getCurrentUser();
      setUser(data);
      setError(null);
    } catch (err) {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const token =
      typeof document !== 'undefined' &&
      document.cookie.includes('nc_access_token=');
  
    if (token) {
      loadUser();
    } else {
      setIsLoading(false);
    }
  }, [loadUser]);

  const signIn = useCallback(
    async (credentials) => {
      setError(null);
      const data = await authService.login(credentials);
      setUser(data.user);
      return data;
    },
    []
  );

  const signOut = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
      router.push(ROUTES.LOGIN);
    }
  }, [router]);

  const updateUser = useCallback((partial) => {
    setUser((prev) => (prev ? { ...prev, ...partial } : prev));
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      error,
      signIn,
      signOut,
      updateUser,
      refresh: loadUser,
    }),
    [user, isLoading, error, signIn, signOut, updateUser, loadUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}