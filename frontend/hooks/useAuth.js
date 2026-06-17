// hooks/useAuth.js

import { useCallback, useEffect, useState } from 'react';
import { useAuthContext } from '@/context/AuthContext';
import { hasPermission, hasAnyPermission, isRoleAtLeast } from '@/lib/permissions';
import { listApiKeys, listSessions, listTeamMembers } from '@/services/auth';

export function useAuth() {
  const context = useAuthContext();

  const can = (permission) => hasPermission(context.user?.role, permission);
  const canAny = (permissions) => hasAnyPermission(context.user?.role, permissions);
  const isAtLeast = (role) => isRoleAtLeast(context.user?.role, role);

  return {
    ...context,
    can,
    canAny,
    isAtLeast,
  };
}

export function useApiKeys() {
  const [apiKeys, setApiKeys] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listApiKeys();
      setApiKeys(data?.items || []);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { apiKeys, isLoading, error, refresh };
}

export function useSessions() {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listSessions();
      setSessions(data?.items || []);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { sessions, isLoading, error, refresh };
}

export function useTeamMembers() {
  const [members, setMembers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listTeamMembers();
      setMembers(data?.items || []);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { members, isLoading, error, refresh };
}
