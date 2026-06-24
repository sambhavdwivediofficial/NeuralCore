// frontend/hooks/useReranking.js

import { useCallback, useEffect, useState } from 'react';
import { apiGet, apiPost } from '@/services/api';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export function useRerankingStrategies() {
  const [strategies, setStrategies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiGet('/reranking/strategies')
      .then((data) => setStrategies(Array.isArray(data) ? data : data.items ?? []))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return { strategies, isLoading };
}

export function useRerankingCompare() {
  const [comparison, setComparison] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const compare = useCallback(async (payload) => {
    setIsLoading(true);
    setComparison(null);
    try {
      const data = await apiPost('/reranking/compare', payload);
      setComparison(data);
      return data;
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => setComparison(null), []);

  return { comparison, isLoading, compare, reset };
}

export function useRerankingMetrics(kbId, range = '7d') {
  const [metrics, setMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!kbId) return;
    apiGet('/reranking/metrics', { params: { knowledge_base_id: kbId, range } })
      .then(setMetrics)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [kbId, range]);

  return { metrics, isLoading };
}
