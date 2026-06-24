// frontend/hooks/useWorkspaces.js

import { useEffect, useState } from 'react';
import * as workspaceService from '@/services/workspaces';
import { getErrorMessage } from '@/lib/axios';

export function useWorkspaces() {
  const [workspaces, setWorkspaces] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    workspaceService.listWorkspaces()
      .then((data) => setWorkspaces(Array.isArray(data) ? data : data.items ?? []))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, []);

  return { workspaces, isLoading, error };
}
