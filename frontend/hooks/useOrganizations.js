// frontend/hooks/useOrganizations.js

import { useCallback, useEffect, useState } from 'react';
import * as orgService from '@/services/organizations';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export function useOrganizations() {
  const [organizations, setOrganizations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await orgService.listOrganizations();
      setOrganizations(Array.isArray(data) ? data : data.items ?? []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const createOrganization = useCallback(async (payload) => {
    const data = await orgService.createOrganization(payload);
    setOrganizations((prev) => [data, ...prev]);
    toast.success('Organization created');
    return data;
  }, []);

  const updateOrganization = useCallback(async (orgId, payload) => {
    const data = await orgService.updateOrganization(orgId, payload);
    setOrganizations((prev) => prev.map((o) => (o.id === orgId ? data : o)));
    toast.success('Organization updated');
    return data;
  }, []);

  return { organizations, isLoading, error, refresh: fetch, createOrganization, updateOrganization };
}

export function useOrganization(orgId) {
  const [organization, setOrganization] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!orgId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await orgService.getOrganization(orgId);
      setOrganization(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  useEffect(() => { fetch(); }, [fetch]);

  const update = useCallback(async (payload) => {
    const data = await orgService.updateOrganization(orgId, payload);
    setOrganization(data);
    toast.success('Organization updated');
    return data;
  }, [orgId]);

  return { organization, isLoading, error, refresh: fetch, update };
}
