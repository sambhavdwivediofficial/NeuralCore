// hooks/useAgents.js

import { useCallback, useEffect, useState } from 'react';
import * as agentsService from '@/services/agents';
import { getErrorMessage } from '@/lib/axios';
import { POLLING_INTERVALS } from '@/lib/constants';

export function useAgents(params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAgents = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await agentsService.listAgents(params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  return {
    agents: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchAgents,
  };
}

export function useAgent(agentId) {
  const [agent, setAgent] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAgent = useCallback(async () => {
    if (!agentId) return;
    setIsLoading(true);
    try {
      const result = await agentsService.getAgent(agentId);
      setAgent(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    fetchAgent();
    const interval = setInterval(fetchAgent, POLLING_INTERVALS.AGENT_STATUS);
    return () => clearInterval(interval);
  }, [fetchAgent]);

  return {
    agent,
    isLoading,
    error,
    refresh: fetchAgent,
  };
}

export function useAgentRuns(agentId, params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRuns = useCallback(async () => {
    if (!agentId) return;
    setIsLoading(true);
    try {
      const result = await agentsService.getAgentRuns(agentId, params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [agentId, JSON.stringify(params)]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  return {
    runs: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchRuns,
  };
}

export function useAvailableTools() {
  const [tools, setTools] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    agentsService
      .getAvailableTools()
      .then((result) => {
        if (active) {
          setTools(result?.items || []);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) setError(getErrorMessage(err));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { tools, isLoading, error };
}