// components/agents/AgentRunner.jsx

'use client';

import { useEffect, useRef, useState } from 'react';
import { Play, Square, CheckCircle2, XCircle, Loader2, Circle, Bot } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { Textarea } from '@/components/common/Textarea';
import { EmptyState } from '@/components/common/EmptyState';
import { useAgentContext } from '@/context/AgentContext';
import { AGENT_STEP_STATE } from '@/lib/constants';
import { formatMs } from '@/lib/utils';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import '@/styles/agents.css';

const STEP_ICON = {
  [AGENT_STEP_STATE.PENDING]: Circle,
  [AGENT_STEP_STATE.RUNNING]: Loader2,
  [AGENT_STEP_STATE.COMPLETE]: CheckCircle2,
  [AGENT_STEP_STATE.ERROR]: XCircle,
};

export function AgentRunner({ agentId }) {
  const { startRun, stopRun, getRun } = useAgentContext();
  const [input, setInput] = useState('');
  const [runId, setRunId] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const outputRef = useRef(null);

  const run = runId ? getRun(runId) : null;

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [run?.output]);

  const handleStart = async () => {
    if (!input.trim()) return;
    setIsStarting(true);
    try {
      const newRunId = await startRun(agentId, { input });
      setRunId(newRunId);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    if (!runId) return;
    try {
      await stopRun(agentId, runId);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  const isRunning = run?.status === 'running';

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Textarea
          rows={3}
          placeholder="Describe the task for this agent..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isRunning}
        />
        <div className="flex justify-end gap-2">
          {isRunning ? (
            <Button variant="destructive" size="sm" onClick={handleStop}>
              <Square className="h-3.5 w-3.5" />
              Stop
            </Button>
          ) : (
            <Button size="sm" onClick={handleStart} isLoading={isStarting} disabled={!input.trim()}>
              <Play className="h-3.5 w-3.5" />
              Run agent
            </Button>
          )}
        </div>
      </div>

      {!run ? (
        <EmptyState
          icon={Bot}
          title="No active run"
          description="Provide a task above and run the agent to see live execution steps."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card-surface p-4">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Execution timeline</h3>
            <div className="agent-timeline">
              {run.steps.length === 0 ? (
                <p className="text-xs text-muted-foreground">Waiting for first step...</p>
              ) : (
                run.steps.map((step) => {
                  const Icon = STEP_ICON[step.state] || Circle;
                  return (
                    <div key={step.id} className="agent-step">
                      <div className="agent-step-marker" data-state={step.state}>
                        <Icon
                          className={`h-3 w-3 ${
                            step.state === AGENT_STEP_STATE.RUNNING ? 'animate-spin' : ''
                          }`}
                        />
                      </div>
                      <div className="flex flex-1 flex-col gap-0.5 pb-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-foreground">{step.title}</span>
                          {step.duration_ms ? (
                            <span className="text-2xs text-muted-foreground">
                              {formatMs(step.duration_ms)}
                            </span>
                          ) : null}
                        </div>
                        {step.detail ? (
                          <p className="text-xs text-muted-foreground">{step.detail}</p>
                        ) : null}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="card-surface flex flex-col p-4">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Output</h3>
            <div
              ref={outputRef}
              className="scrollbar-thin min-h-[12rem] flex-1 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-foreground"
            >
              {run.output || (
                <span className="text-xs text-muted-foreground">
                  Output will stream here as the agent generates a response.
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
