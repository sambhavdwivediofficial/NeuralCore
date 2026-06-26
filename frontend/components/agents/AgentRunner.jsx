// frontend/components/agents/AgentRunner.jsx

'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Play, Square, CheckCircle2, XCircle, Loader2, Circle, Bot, Zap } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { Textarea } from '@/components/common/Textarea';
import { EmptyState } from '@/components/common/EmptyState';
import { Badge } from '@/components/common/Badge';
import { runAgent, stopAgent, getAgentRun } from '@/services/agents';
import { AGENT_STEP_STATE } from '@/lib/constants';
import { formatMs, cn } from '@/lib/utils';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import '@/styles/agents.css';

const STEP_ICON = {
  [AGENT_STEP_STATE.PENDING]: Circle,
  [AGENT_STEP_STATE.RUNNING]: Loader2,
  [AGENT_STEP_STATE.COMPLETE]: CheckCircle2,
  [AGENT_STEP_STATE.ERROR]: XCircle,
};

const STATUS_VARIANT = {
  running: 'default',
  completed: 'success',
  failed: 'destructive',
  stopped: 'warning',
  unknown: 'muted',
};

export function AgentRunner({ agentId }) {
  const [input, setInput] = useState('');
  const [run, setRun] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const outputRef = useRef(null);
  const pollRef = useRef(null);

  // Auto-scroll output
  useEffect(() => {
    if (outputRef.current && run?.output) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [run?.output]);

  // Start polling when run is active
  const startPolling = useCallback((runId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    
    setIsPolling(true);
    
    const poll = async () => {
      try {
        const updated = await getAgentRun(agentId, runId);
        setRun(updated);
        
        if (updated.status !== 'running') {
          clearInterval(pollRef.current);
          setIsPolling(false);
        }
      } catch (err) {
        console.error('Poll error:', err);
      }
    };
    
    // Immediate first poll
    poll();
    pollRef.current = setInterval(poll, 2000);
  }, [agentId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleStart = async () => {
    if (!input.trim()) return;
    setIsStarting(true);
    try {
      const result = await runAgent(agentId, { input: input.trim() });
      setRun(result);
      setInput('');
      
      // Start polling for updates
      if (result.run_id) {
        startPolling(result.run_id);
      }
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    if (!run?.run_id && !run?.id) return;
    const runId = run.run_id || run.id;
    
    try {
      await stopAgent(agentId, runId);
      if (pollRef.current) {
        clearInterval(pollRef.current);
        setIsPolling(false);
      }
      const updated = await getAgentRun(agentId, runId);
      setRun(updated);
      toast.success('Agent stopped');
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  const isRunning = run?.status === 'running' || run?.status === 'started';
  const runStatus = run?.status || 'unknown';
  const steps = run?.steps || [];
  const output = run?.output || run?.response || '';

  return (
    <div className="flex flex-col gap-4">
      {/* Input Section */}
      <div className="flex flex-col gap-2">
        <Textarea
          rows={3}
          placeholder="Describe the task for this agent..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isRunning}
        />
        <div className="flex items-center justify-between">
          {run && (
            <div className="flex items-center gap-2">
              <Badge variant={STATUS_VARIANT[runStatus] || 'muted'}>
                {runStatus}
              </Badge>
              {isPolling && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Polling...
                </span>
              )}
              {run.error && (
                <span className="text-xs text-destructive">{run.error}</span>
              )}
            </div>
          )}
          <div className="flex gap-2 ml-auto">
            {isRunning ? (
              <Button variant="destructive" size="sm" onClick={handleStop}>
                <Square className="h-3.5 w-3.5" />
                Stop
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={handleStart}
                isLoading={isStarting}
                disabled={!input.trim()}
              >
                <Play className="h-3.5 w-3.5" />
                Run agent
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Results Section */}
      {!run ? (
        <EmptyState
          icon={Bot}
          title="No active run"
          description="Provide a task above and run the agent."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Timeline */}
          <div className="card-surface p-4">
            <h3 className="mb-3 text-sm font-semibold text-foreground flex items-center gap-2">
              Execution timeline
              {run.model && (
                <Badge variant="muted" className="text-2xs">
                  <Zap className="h-2.5 w-2.5 mr-0.5" />
                  {run.model}
                </Badge>
              )}
            </h3>
            <div className="agent-timeline">
              {steps.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  {isRunning ? 'Running...' : 'No steps recorded'}
                </p>
              ) : (
                steps.map((step, index) => {
                  const Icon = STEP_ICON[step.state] || Circle;
                  return (
                    <div key={step.id || index} className="agent-step">
                      <div className="agent-step-marker" data-state={step.state}>
                        <Icon
                          className={cn(
                            'h-3 w-3',
                            step.state === AGENT_STEP_STATE.RUNNING && 'animate-spin'
                          )}
                        />
                      </div>
                      <div className="flex flex-1 flex-col gap-0.5 pb-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-foreground">
                            {step.title || `Step ${index + 1}`}
                          </span>
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
            
            {/* Metrics */}
            {run.total_duration_ms && (
              <div className="mt-3 pt-3 border-t border-border grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                <div>
                  <span className="block text-2xs uppercase">Duration</span>
                  {formatMs(run.total_duration_ms)}
                </div>
                <div>
                  <span className="block text-2xs uppercase">Tokens</span>
                  {run.eval_count || '—'}
                </div>
                <div>
                  <span className="block text-2xs uppercase">Prompt Tokens</span>
                  {run.prompt_eval_count || '—'}
                </div>
              </div>
            )}
          </div>

          {/* Output */}
          <div className="card-surface flex flex-col p-4">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Output</h3>
            <div
              ref={outputRef}
              className="scrollbar-thin min-h-[12rem] max-h-[15rem] flex-1 overflow-y-auto whitespace-pre-wrap rounded-md bg-background p-3 text-sm leading-relaxed text-foreground font-mono"
            >
              {output || (
                <span className="text-xs text-muted-foreground">
                  {isRunning ? 'Waiting for response...' : 'No output generated'}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
