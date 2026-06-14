// hooks/useProjects.js

import { useCallback, useEffect, useState } from 'react';
import * as projectsService from '@/services/projects';
import { getErrorMessage } from '@/lib/axios';

export function useProjects(params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProjects = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await projectsService.listProjects(params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return {
    projects: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchProjects,
  };
}

export function useProject(projectId) {
  const [project, setProject] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProject = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    try {
      const result = await projectsService.getProject(projectId);
      setProject(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  return {
    project,
    isLoading,
    error,
    refresh: fetchProject,
  };
}

export function useProjectAnalytics(projectId, params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAnalytics = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    try {
      const result = await projectsService.getProjectAnalytics(projectId, params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [projectId, JSON.stringify(params)]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return {
    analytics: data,
    isLoading,
    error,
    refresh: fetchAnalytics,
  };
}