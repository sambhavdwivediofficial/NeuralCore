// frontend/context/OrganizationContext.jsx

'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as orgService from '@/services/organizations';
import { useAuthContext } from '@/context/AuthContext';

const OrganizationContext = createContext(null);

export function OrganizationProvider({ children }) {
  const { user, isAuthenticated } = useAuthContext();
  const [organizations, setOrganizations] = useState([]);
  const [activeOrg, setActiveOrg] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    if (!isAuthenticated) { setIsLoading(false); return; }
    setIsLoading(true);
    try {
      const data = await orgService.listOrganizations();
      const list = Array.isArray(data) ? data : data.items ?? [];
      setOrganizations(list);
      const stored = typeof window !== 'undefined' ? localStorage.getItem('nc_active_org') : null;
      const found = list.find((o) => o.id === stored) ?? list[0] ?? null;
      setActiveOrg(found);
    } catch {
      setOrganizations([]);
      setActiveOrg(null);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => { load(); }, [load]);

  const switchOrg = useCallback((org) => {
    setActiveOrg(org);
    if (typeof window !== 'undefined') {
      localStorage.setItem('nc_active_org', org.id);
    }
  }, []);

  const addOrg = useCallback((org) => {
    setOrganizations((prev) => [org, ...prev]);
    setActiveOrg(org);
    if (typeof window !== 'undefined') {
      localStorage.setItem('nc_active_org', org.id);
    }
  }, []);

  const updateActiveOrg = useCallback((partial) => {
    setActiveOrg((prev) => prev ? { ...prev, ...partial } : prev);
    setOrganizations((prev) =>
      prev.map((o) => (o.id === partial.id ? { ...o, ...partial } : o))
    );
  }, []);

  const value = useMemo(() => ({
    organizations,
    activeOrg,
    isLoading,
    switchOrg,
    addOrg,
    updateActiveOrg,
    refresh: load,
  }), [organizations, activeOrg, isLoading, switchOrg, addOrg, updateActiveOrg, load]);

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganizationContext() {
  const ctx = useContext(OrganizationContext);
  if (!ctx) throw new Error('useOrganizationContext must be used within OrganizationProvider');
  return ctx;
}
