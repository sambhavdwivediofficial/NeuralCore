// context/AgentContext.jsx

'use client';

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';
import * as agentsService from '@/services/agents';
import { AGENT_STEP_STATE } from '@/lib/constants';

const AgentContext = createContext(null);

export function AgentProvider({ children }) {
  const [activeRuns, setActiveRuns] = useState({});
  const stopFnsRef = useRef({});

  const startRun = useCallback(async (agentId, payload) => {
    const data = await agentsService.runAgent(agentId, payload);
    const runId = data.run_id;

    setActiveRuns((prev) => ({
      ...prev,
      [runId]: {
        runId,
        agentId,
        status: 'running',
        steps: [],
        output: '',
        startedAt: new Date().toISOString(),
      },
    }));

    const stop = agentsService.streamAgentRun(
      agentId,
      runId,
      (event) => {
        setActiveRuns((prev) => {
          const run = prev[runId];
          if (!run) return prev;

          if (event.type === 'step') {
            const steps = [...run.steps];
            const existingIndex = steps.findIndex((step) => step.id === event.step.id);
            if (existingIndex >= 0) {
              steps[existingIndex] = event.step;
            } else {
              steps.push(event.step);
            }
            return {
              ...prev,
              [runId]: { ...run, steps },
            };
          }

          if (event.type === 'token') {
            return {
              ...prev,
              [runId]: { ...run, output: run.output + event.content },
            };
          }

          if (event.type === 'status') {
            return {
              ...prev,
              [runId]: { ...run, status: event.status },
            };
          }

          return prev;
        });
      },
      () => {
        setActiveRuns((prev) => {
          const run = prev[runId];
          if (!run) return prev;
          return { ...prev, [runId]: { ...run, status: 'failed' } };
        });
      },
      () => {
        setActiveRuns((prev) => {
          const run = prev[runId];
          if (!run) return prev;
          if (run.status === 'running') {
            return { ...prev, [runId]: { ...run, status: 'completed' } };
          }
          return prev;
        });
      }
    );

    stopFnsRef.current[runId] = stop;
    return runId;
  }, []);

  const stopRun = useCallback(async (agentId, runId) => {
    await agentsService.stopAgent(agentId);
    const stop = stopFnsRef.current[runId];
    if (stop) stop();
    setActiveRuns((prev) => {
      const run = prev[runId];
      if (!run) return prev;
      return { ...prev, [runId]: { ...run, status: 'failed' } };
    });
  }, []);

  const getRun = useCallback((runId) => activeRuns[runId] || null, [activeRuns]);

  const getRunningStepCount = useCallback(
    (runId) => {
      const run = activeRuns[runId];
      if (!run) return 0;
      return run.steps.filter((step) => step.state === AGENT_STEP_STATE.RUNNING).length;
    },
    [activeRuns]
  );

  const value = useMemo(
    () => ({
      activeRuns,
      startRun,
      stopRun,
      getRun,
      getRunningStepCount,
    }),
    [activeRuns, startRun, stopRun, getRun, getRunningStepCount]
  );

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
}

export function useAgentContext() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgentContext must be used within an AgentProvider');
  }
  return context;
}