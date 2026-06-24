// frontend/hooks/useAdmin.js

import { useCallback, useEffect, useState } from 'react';
import * as adminService from '@/services/admin';
import { getErrorMessage } from '@/lib/axios';

export function useAdminStats() {
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminService.getPlatformStats();
      setStats(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { stats, isLoading, error, refresh: fetch };
}

export function useAdminOrganizations() {
  const [organizations, setOrganizations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminService.listAllOrganizations();
      setOrganizations(Array.isArray(data) ? data : data.items ?? []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { organizations, isLoading, error, refresh: fetch };
}
