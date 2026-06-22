// frontend/hooks/useAuth.js

import { useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';
import * as authService from '@/services/auth';
import { ROUTES } from '@/lib/routes';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';

export function useAuth() {
  const ctx = useAuthContext();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const signIn = useCallback(async (credentials) => {
    setIsLoading(true);
    try {
      const result = await ctx.signIn(credentials);
      if (result.mfa_required) {
        router.push(ROUTES.LOGIN_MFA);
        return result;
      }
      const dest = result.user?.tenant_id || result.tenant_id
        ? ROUTES.DASHBOARD
        : ROUTES.ONBOARDING;
      router.push(dest);
      return result;
    } finally {
      setIsLoading(false);
    }
  }, [ctx, router]);

  const signUp = useCallback(async (payload) => {
    setIsLoading(true);
    try {
      const { confirmPassword, ...body } = payload;
      if (!body.organization_name) delete body.organization_name;
      const data = await authService.signup(body);
      ctx.updateUser(data.user ?? data);
      const dest = (data.user ?? data).tenant_id ? ROUTES.DASHBOARD : ROUTES.ONBOARDING;
      router.push(dest);
      return data;
    } finally {
      setIsLoading(false);
    }
  }, [ctx, router]);

  const completeMfa = useCallback(async (code) => {
    setIsLoading(true);
    try {
      const data = await ctx.completeMfa(code);
      const dest = (data.user ?? data).tenant_id ? ROUTES.DASHBOARD : ROUTES.ONBOARDING;
      router.push(dest);
      return data;
    } finally {
      setIsLoading(false);
    }
  }, [ctx, router]);

  const forgotPassword = useCallback(async (email) => {
    setIsLoading(true);
    try {
      return await authService.forgotPassword(email);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const resetPassword = useCallback(async (token, new_password) => {
    setIsLoading(true);
    try {
      const data = await authService.resetPassword(token, new_password);
      toast.success('Password updated. Please sign in.');
      router.push(ROUTES.LOGIN);
      return data;
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  const verifyEmail = useCallback(async (token) => {
    setIsLoading(true);
    try {
      const data = await authService.verifyEmail(token);
      ctx.updateUser({ is_verified: true });
      return data;
    } finally {
      setIsLoading(false);
    }
  }, [ctx]);

  const acceptInvite = useCallback(async (token, payload) => {
    setIsLoading(true);
    try {
      const data = await authService.acceptInvite({ token, ...payload });
      ctx.updateUser(data.user ?? data);
      router.push(ROUTES.DASHBOARD);
      return data;
    } finally {
      setIsLoading(false);
    }
  }, [ctx, router]);

  const updateProfile = useCallback(async (payload) => {
    setIsLoading(true);
    try {
      const data = await authService.updateProfile(payload);
      ctx.updateUser(data);
      toast.success('Profile updated');
      return data;
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [ctx]);

  const changePassword = useCallback(async (payload) => {
    setIsLoading(true);
    try {
      await authService.changePassword(payload);
      toast.success('Password changed successfully');
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    user: ctx.user,
    isAuthenticated: ctx.isAuthenticated,
    isLoading: ctx.isLoading || isLoading,
    mfaPending: ctx.mfaPending,
    signIn,
    signUp,
    completeMfa,
    signOut: ctx.signOut,
    forgotPassword,
    resetPassword,
    verifyEmail,
    acceptInvite,
    updateProfile,
    changePassword,
    refresh: ctx.refresh,
  };
}
