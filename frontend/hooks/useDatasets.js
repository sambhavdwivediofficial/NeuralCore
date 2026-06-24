// frontend/hooks/useDatasets.js

import { useCallback, useEffect, useState } from 'react';
import * as datasetService from '@/services/datasets';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export function useDatasets(projectId) {
  const [datasets, setDatasets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await datasetService.listDatasets(projectId ? { project_id: projectId } : {});
      setDatasets(Array.isArray(data) ? data : data.items ?? []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetch(); }, [fetch]);

  const create = useCallback(async (payload) => {
    const data = await datasetService.createDataset(payload);
    setDatasets((prev) => [data, ...prev]);
    toast.success('Dataset created');
    return data;
  }, []);

  const update = useCallback(async (id, payload) => {
    const data = await datasetService.updateDataset(id, payload);
    setDatasets((prev) => prev.map((d) => (d.id === id ? data : d)));
    toast.success('Dataset updated');
    return data;
  }, []);

  const remove = useCallback(async (id) => {
    await datasetService.deleteDataset(id);
    setDatasets((prev) => prev.filter((d) => d.id !== id));
    toast.success('Dataset deleted');
  }, []);

  return { datasets, isLoading, error, refresh: fetch, create, update, remove };
}
