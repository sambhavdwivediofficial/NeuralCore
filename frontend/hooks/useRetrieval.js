// hooks/useRetrieval.js

import { useCallback, useEffect, useState } from 'react';
import * as retrievalService from '@/services/retrieval';
import { getErrorMessage } from '@/lib/axios';

export function useRetrievalQuery() {
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const runQuery = useCallback(async (payload) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await retrievalService.runRetrievalQuery(payload);
      setResult(data);
      return data;
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isLoading, error, runQuery, reset };
}

export function useRetrievalTraces(params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTraces = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await retrievalService.listRetrievalTraces(params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  return {
    traces: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchTraces,
  };
}

export function useRetrievalMetrics(kbId, params) {
  const [metrics, setMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = useCallback(async () => {
    if (!kbId) return;
    setIsLoading(true);
    try {
      const result = await retrievalService.getRetrievalMetrics(kbId, params);
      setMetrics(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [kbId, JSON.stringify(params)]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { metrics, isLoading, error, refresh: fetchMetrics };
}