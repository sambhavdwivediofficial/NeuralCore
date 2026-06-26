// frontend/hooks/useAgents.js

import { useCallback, useEffect, useState } from 'react';
import * as agentsService from '@/services/agents';
import { getErrorMessage } from '@/lib/axios';
import { POLLING_INTERVALS } from '@/lib/constants';

function isValidUUID(str) {
  if (!str || typeof str !== 'string') return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

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
  }, [params?.project_id, params?.search, params?.type, params?.page, params?.page_size]);

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
    if (!agentId || !isValidUUID(agentId)) {
      setIsLoading(false);
      setError('Invalid agent ID');
      return;
    }
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
    // Polling only when agent is in running state
    // const interval = agent?.status === 'running' 
    //   ? setInterval(fetchAgent, POLLING_INTERVALS.AGENT_STATUS) 
    //   : null;
    // return () => {
    //   if (interval) clearInterval(interval);
    // };
  }, [fetchAgent, agent?.status]);

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
    if (!agentId || !isValidUUID(agentId)) {
      setIsLoading(false);
      setError('Invalid agent ID');
      return;
    }
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
  }, [agentId, params?.page, params?.page_size]);

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
