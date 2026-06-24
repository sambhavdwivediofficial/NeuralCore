// frontend/hooks/useVision.js

import { useCallback, useState } from 'react';
import * as visionService from '@/services/vision';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export function useImageAnalyze() {
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const analyze = useCallback(async (file, question = '') => {
    setIsLoading(true);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      if (question) fd.append('question', question);
      const data = await visionService.analyzeImage(fd);
      setResult(data);
      return data;
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const extractText = useCallback(async (file) => {
    setIsLoading(true);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const data = await visionService.extractText(fd);
      setResult(data);
      return data;
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => setResult(null), []);

  return { result, isLoading, analyze, extractText, reset };
}
