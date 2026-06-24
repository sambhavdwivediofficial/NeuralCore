// frontend/hooks/usePrompts.js

import { useCallback, useEffect, useState } from 'react';
import * as promptService from '@/services/prompts';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export function usePrompts() {
  const [templates, setTemplates] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await promptService.listPromptTemplates();
      setTemplates(Array.isArray(data) ? data : data.items ?? []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { templates, isLoading, error, refresh: fetch };
}

export function usePromptRender() {
  const [rendered, setRendered] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const render = useCallback(async (templateName, variables) => {
    setIsLoading(true);
    try {
      const data = await promptService.renderPrompt({ template_name: templateName, variables });
      setRendered(data.rendered);
      return data;
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => setRendered(null), []);

  return { rendered, isLoading, render, reset };
}
