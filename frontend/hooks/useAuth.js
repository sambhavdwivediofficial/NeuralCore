// frontend/hooks/useAuth.js

import { useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthContext } from '@/context/AuthContext';
import * as authService from '@/services/auth';
import { ROUTES } from '@/lib/routes';
import { AUTH_COOKIE_NAME } from '@/lib/constants';
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
      if (result.access_token) {
        document.cookie = `${AUTH_COOKIE_NAME}=${result.access_token}; path=/; max-age=2592000; SameSite=Lax`;
        localStorage.setItem('nc_token', result.access_token);
      }
      const dest = result.user?.tenant_id || result.tenant_id
        ? ROUTES.DASHBOARD
        : ROUTES.ONBOARDING;
      window.location.href = dest;
      return result;
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
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
      if (data.access_token) {
        document.cookie = `${AUTH_COOKIE_NAME}=${data.access_token}; path=/; max-age=2592000; SameSite=Lax`;
        localStorage.setItem('nc_token', data.access_token);
      }
      const dest = (data.user ?? data).tenant_id ? ROUTES.DASHBOARD : ROUTES.ONBOARDING;
      window.location.href = dest;
      return data;
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [ctx]);

  const completeMfa = useCallback(async (code) => {
    setIsLoading(true);
    try {
      const data = await ctx.completeMfa(code);
      if (data.access_token) {
        document.cookie = `${AUTH_COOKIE_NAME}=${data.access_token}; path=/; max-age=2592000; SameSite=Lax`;
        localStorage.setItem('nc_token', data.access_token);
      }
      const dest = (data.user ?? data).tenant_id ? ROUTES.DASHBOARD : ROUTES.ONBOARDING;
      window.location.href = dest;
      return data;
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [ctx]);

  const forgotPassword = useCallback(async (email) => {
    setIsLoading(true);
    try {
      return await authService.forgotPassword(email);
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
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
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
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
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [ctx]);

  const acceptInvite = useCallback(async (token, payload) => {
    setIsLoading(true);
    try {
      const data = await authService.acceptInvite({ token, ...payload });
      ctx.updateUser(data.user ?? data);
      if (data.access_token) {
        document.cookie = `${AUTH_COOKIE_NAME}=${data.access_token}; path=/; max-age=2592000; SameSite=Lax`;
        localStorage.setItem('nc_token', data.access_token);
      }
      window.location.href = ROUTES.DASHBOARD;
      return data;
    } catch (error) {
      toast.error(getErrorMessage(error));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [ctx]);

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
