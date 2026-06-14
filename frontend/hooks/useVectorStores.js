// hooks/useVectorStores.js

import { useCallback, useEffect, useState } from 'react';
import * as vectorStoresService from '@/services/vectorstores';
import { getErrorMessage } from '@/lib/axios';
import { POLLING_INTERVALS } from '@/lib/constants';

export function useVectorStores() {
  const [stores, setStores] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStores = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await vectorStoresService.listVectorStores();
      setStores(result?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStores();
  }, [fetchStores]);

  return { stores, isLoading, error, refresh: fetchStores };
}

export function useVectorStoreMetrics(storeId, params) {
  const [metrics, setMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = useCallback(async () => {
    if (!storeId) return;
    setIsLoading(true);
    try {
      const result = await vectorStoresService.getVectorStoreMetrics(storeId, params);
      setMetrics(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [storeId, JSON.stringify(params)]);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, POLLING_INTERVALS.METRICS);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  return { metrics, isLoading, error, refresh: fetchMetrics };
}

export function useVectorStoreCollections(storeId) {
  const [collections, setCollections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCollections = useCallback(async () => {
    if (!storeId) return;
    setIsLoading(true);
    try {
      const result = await vectorStoresService.getVectorStoreCollections(storeId);
      setCollections(result?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [storeId]);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  return { collections, isLoading, error, refresh: fetchCollections };
}