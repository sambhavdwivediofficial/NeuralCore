// components/agents/AgentCard.jsx

import { MoreHorizontal, Play, Settings, Trash2 } from 'lucide-react';
import { Button } from '@/components/common/Button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/common/DropdownMenu';
import { AGENT_TYPE_LABELS } from '@/lib/constants';
import { formatRelativeTime } from '@/lib/utils';
import '@/styles/agents.css';

export function AgentCard({ agent, onOpen, onRun, onSettings, onDelete }) {
  return (
    <div className="agent-card">
      <div className="flex items-start justify-between gap-2">
        <button onClick={() => onOpen?.(agent)} className="flex flex-1 items-start gap-3 text-left">
          <div className="agent-type-icon">
            <span className="text-xs font-semibold uppercase">{agent.type?.slice(0, 2)}</span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-foreground">{agent.name}</span>
            <span className="text-xs text-muted-foreground">
              {AGENT_TYPE_LABELS[agent.type] || agent.type}
            </span>
          </div>
        </button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="iconSm" onClick={(e) => e.stopPropagation()}>
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onRun?.(agent)}>
              <Play className="h-3.5 w-3.5" />
              Run agent
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onSettings?.(agent)}>
              <Settings className="h-3.5 w-3.5" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => onDelete?.(agent)}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {agent.description ? (
        <p className="line-clamp-2 text-xs text-muted-foreground">{agent.description}</p>
      ) : null}

      <div className="flex items-center justify-between">
        <span className="agent-status-badge" data-status={agent.status}>
          <span className="status-dot bg-current" />
          {agent.status}
        </span>
        <span className="text-2xs text-muted-foreground">
          Updated {formatRelativeTime(agent.updated_at)}
        </span>
      </div>
    </div>
  );
}
