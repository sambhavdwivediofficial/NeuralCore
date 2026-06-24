// frontend/hooks/usePipelines.js

import { useCallback, useEffect, useState } from 'react';
import * as pipelineService from '@/services/pipelines';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export function usePipelines() {
  const [pipelines, setPipelines] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    pipelineService.listPipelines()
      .then((data) => setPipelines(Array.isArray(data) ? data : data.items ?? []))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return { pipelines, isLoading };
}

export function usePipelineRun() {
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const run = useCallback(async (payload) => {
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await pipelineService.runPipeline(payload);
      setResult(data);
      return data;
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      toast.error(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isLoading, error, run, reset };
}
