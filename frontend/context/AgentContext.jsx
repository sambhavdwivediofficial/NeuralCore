// frontend/context/AgentContext.jsx

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
  const pollIntervalsRef = useRef({});

  const startPolling = useCallback((agentId, runId) => {
    // Clear any existing poll interval
    if (pollIntervalsRef.current[runId]) {
      clearInterval(pollIntervalsRef.current[runId]);
    }

    const poll = async () => {
      try {
        const updatedRun = await agentsService.getAgentRun(agentId, runId);
        
        setActiveRuns((prev) => {
          const existing = prev[runId];
          if (!existing) return prev;

          return {
            ...prev,
            [runId]: {
              ...existing,
              status: updatedRun.status || existing.status,
              steps: updatedRun.steps || existing.steps || [],
              output: updatedRun.output || existing.output || '',
            },
          };
        });

        // Stop polling when run completes or fails
        if (updatedRun.status === 'completed' || updatedRun.status === 'failed') {
          clearInterval(pollIntervalsRef.current[runId]);
          delete pollIntervalsRef.current[runId];
        }
      } catch (error) {
        console.error('Poll error for run:', runId, error);
      }
    };

    // Initial poll
    poll();

    // Start interval polling
    pollIntervalsRef.current[runId] = setInterval(poll, 2000);
  }, []);

  const startRun = useCallback(async (agentId, payload) => {
    try {
      const data = await agentsService.runAgent(agentId, payload);
      const runId = data.run_id || data.id;

      if (!runId) {
        throw new Error('No run_id returned from server');
      }

      // Initialize run state
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

      // Try SSE stream, fallback to polling on failure
      let streamActive = false;

      try {
        const stop = agentsService.streamAgentRun(
          agentId,
          runId,
          // onMessage
          (event) => {
            streamActive = true;
            setActiveRuns((prev) => {
              const run = prev[runId];
              if (!run) return prev;

              if (event.type === 'step') {
                const steps = [...(run.steps || [])];
                const existingIndex = steps.findIndex((step) => step.id === event.step?.id);
                if (existingIndex >= 0) {
                  steps[existingIndex] = event.step;
                } else if (event.step) {
                  steps.push(event.step);
                }
                return {
                  ...prev,
                  [runId]: { ...run, steps },
                };
              }

              if (event.type === 'token' && event.content) {
                return {
                  ...prev,
                  [runId]: { ...run, output: (run.output || '') + event.content },
                };
              }

              if (event.type === 'status' && event.status) {
                return {
                  ...prev,
                  [runId]: { ...run, status: event.status },
                };
              }

              return prev;
            });
          },
          // onError
          (error) => {
            console.warn('SSE stream error, switching to polling:', error);
            if (!streamActive) {
              startPolling(agentId, runId);
            }
          },
          // onComplete
          () => {
            if (!streamActive) {
              startPolling(agentId, runId);
            } else {
              setActiveRuns((prev) => {
                const run = prev[runId];
                if (!run) return prev;
                if (run.status === 'running') {
                  return { ...prev, [runId]: { ...run, status: 'completed' } };
                }
                return prev;
              });
            }
          }
        );

        stopFnsRef.current[runId] = stop;

        // Set timeout to detect if stream is not sending events
        setTimeout(() => {
          if (!streamActive) {
            console.warn('No stream events received after 3s, switching to polling');
            startPolling(agentId, runId);
          }
        }, 3000);

      } catch (streamError) {
        console.warn('Failed to create SSE stream, using polling:', streamError);
        startPolling(agentId, runId);
      }

      return runId;
    } catch (error) {
      console.error('Failed to start run:', error);
      throw error;
    }
  }, [startPolling]);

  const stopRun = useCallback(async (agentId, runId) => {
    try {
      await agentsService.stopAgent(agentId, runId);
    } catch (error) {
      console.error('Stop API error:', error);
    }

    // Stop SSE stream if active
    const stop = stopFnsRef.current[runId];
    if (stop) {
      try { stop(); } catch (e) { /* ignore */ }
      delete stopFnsRef.current[runId];
    }

    // Stop polling if active
    if (pollIntervalsRef.current[runId]) {
      clearInterval(pollIntervalsRef.current[runId]);
      delete pollIntervalsRef.current[runId];
    }

    // Update status
    setActiveRuns((prev) => {
      const run = prev[runId];
      if (!run) return prev;
      return { ...prev, [runId]: { ...run, status: 'stopped' } };
    });
  }, []);

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    Object.values(stopFnsRef.current).forEach((stop) => {
      try { stop(); } catch (e) { /* ignore */ }
    });
    Object.values(pollIntervalsRef.current).forEach((interval) => {
      clearInterval(interval);
    });
  }, []);

  const getRun = useCallback((runId) => activeRuns[runId] || null, [activeRuns]);

  const getRunningStepCount = useCallback(
    (runId) => {
      const run = activeRuns[runId];
      if (!run?.steps) return 0;
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
      cleanup,
    }),
    [activeRuns, startRun, stopRun, getRun, getRunningStepCount, cleanup]
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
