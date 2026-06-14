// hooks/useEmbeddings.js

import { useCallback, useEffect, useState } from 'react';
import * as embeddingsService from '@/services/embeddings';
import { getErrorMessage } from '@/lib/axios';

export function useEmbeddingProviders() {
  const [providers, setProviders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProviders = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await embeddingsService.listEmbeddingProviders();
      setProviders(result?.items || []);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  return { providers, isLoading, error, refresh: fetchProviders };
}

export function useEmbeddingVisualization(kbId, params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchVisualization = useCallback(async () => {
    if (!kbId) return;
    setIsLoading(true);
    try {
      const result = await embeddingsService.getEmbeddingVisualization(kbId, params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [kbId, JSON.stringify(params)]);

  useEffect(() => {
    fetchVisualization();
  }, [fetchVisualization]);

  return {
    points: data?.points || [],
    dimensions: data?.dimensions || 0,
    isLoading,
    error,
    refresh: fetchVisualization,
  };
}

export function useEmbeddingCacheStats() {
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await embeddingsService.getEmbeddingCacheStats();
      setStats(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, isLoading, error, refresh: fetchStats };
}