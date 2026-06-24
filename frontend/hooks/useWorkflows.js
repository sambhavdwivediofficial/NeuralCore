// frontend/hooks/useWorkflows.js

import { useCallback, useEffect, useState } from 'react';
import * as workflowService from '@/services/workflows';
import { getErrorMessage } from '@/lib/axios';
import { toast } from '@/components/common/Toast';

export function useWorkflows(projectId) {
  const [workflows, setWorkflows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await workflowService.listWorkflows(projectId ? { project_id: projectId } : {});
      setWorkflows(Array.isArray(data) ? data : data.items ?? []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetch(); }, [fetch]);

  const create = useCallback(async (payload) => {
    const data = await workflowService.createWorkflow(payload);
    setWorkflows((prev) => [data, ...prev]);
    toast.success('Workflow created');
    return data;
  }, []);

  const update = useCallback(async (id, payload) => {
    const data = await workflowService.updateWorkflow(id, payload);
    setWorkflows((prev) => prev.map((w) => (w.id === id ? data : w)));
    toast.success('Workflow updated');
    return data;
  }, []);

  const remove = useCallback(async (id) => {
    await workflowService.deleteWorkflow(id);
    setWorkflows((prev) => prev.filter((w) => w.id !== id));
    toast.success('Workflow deleted');
  }, []);

  return { workflows, isLoading, error, refresh: fetch, create, update, remove };
}

export function useWorkflow(workflowId) {
  const [workflow, setWorkflow] = useState(null);
  const [runs, setRuns] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!workflowId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [wf, runData] = await Promise.all([
        workflowService.getWorkflow(workflowId),
        workflowService.listWorkflowRuns(workflowId),
      ]);
      setWorkflow(wf);
      setRuns(Array.isArray(runData) ? runData : runData.items ?? []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [workflowId]);

  useEffect(() => { fetch(); }, [fetch]);

  const run = useCallback(async (input = {}) => {
    setRunLoading(true);
    try {
      const data = await workflowService.runWorkflow(workflowId, input);
      toast.success('Workflow started');
      await fetch();
      return data;
    } catch (err) {
      toast.error(getErrorMessage(err));
      throw err;
    } finally {
      setRunLoading(false);
    }
  }, [workflowId, fetch]);

  return { workflow, runs, isLoading, runLoading, error, refresh: fetch, run };
}
