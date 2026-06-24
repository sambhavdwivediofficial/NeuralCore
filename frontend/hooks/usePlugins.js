// frontend/hooks/usePlugins.js

import { useEffect, useState } from 'react';
import * as pluginService from '@/services/plugins';
import { getErrorMessage } from '@/lib/axios';

export function usePlugins() {
  const [plugins, setPlugins] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    pluginService.listPlugins()
      .then((data) => setPlugins(Array.isArray(data) ? data : data.items ?? []))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, []);

  return { plugins, isLoading, error };
}
