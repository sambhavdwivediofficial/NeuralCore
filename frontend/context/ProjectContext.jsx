// context/ProjectContext.jsx

'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import * as projectsService from '@/services/projects';

const ProjectContext = createContext(null);

const ACTIVE_PROJECT_KEY = 'nc_active_project_id';

export function ProjectProvider({ children }) {
  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadProjects = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await projectsService.listProjects();
      const items = data?.items || [];
      setProjects(items);

      if (typeof window !== 'undefined') {
        const stored = window.localStorage.getItem(ACTIVE_PROJECT_KEY);
        const exists = items.find((project) => project.id === stored);
        if (exists) {
          setActiveProjectId(stored);
        } else if (items.length > 0) {
          setActiveProjectId(items[0].id);
        }
      }

      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const setActiveProject = useCallback((projectId) => {
    setActiveProjectId(projectId);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(ACTIVE_PROJECT_KEY, projectId);
    }
  }, []);

  const activeProject = useMemo(
    () => projects.find((project) => project.id === activeProjectId) || null,
    [projects, activeProjectId]
  );

  const value = useMemo(
    () => ({
      projects,
      activeProject,
      activeProjectId,
      isLoading,
      error,
      setActiveProject,
      refresh: loadProjects,
    }),
    [projects, activeProject, activeProjectId, isLoading, error, setActiveProject, loadProjects]
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjectContext() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProjectContext must be used within a ProjectProvider');
  }
  return context;
}