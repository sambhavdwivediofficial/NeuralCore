// frontend/components/prompts/PromptPreview.jsx

'use client';

import { useState } from 'react';
import { Play, Copy, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';
import { usePromptRender } from '@/hooks/usePrompts';
import { toast } from '@/components/common/Toast';
import { cn } from '@/lib/utils';

export function PromptPreview({ template }) {
  const { rendered, isLoading, render, reset } = usePromptRender();
  const [variables, setVariables] = useState(() => {
    const init = {};
    (template?.required_variables ?? []).forEach((v) => { init[v] = ''; });
    return init;
  });
  const [collapsed, setCollapsed] = useState(false);

  const handleRender = async () => {
    await render(template.name, variables);
  };

  const handleCopy = () => {
    if (rendered) {
      navigator.clipboard.writeText(rendered).then(() => toast.success('Copied'));
    }
  };

  const allFilled = Object.values(variables).every((v) => v.trim() !== '');

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-foreground font-mono">{template?.name}</span>
        </div>
        <button type="button" onClick={() => setCollapsed((p) => !p)}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
          {collapsed ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
        </button>
      </div>

      {!collapsed && (
        <div className="flex flex-col gap-4 px-4 pb-4">
          {(template?.required_variables ?? []).length > 0 && (
            <div className="flex flex-col gap-3">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Variables</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {(template?.required_variables ?? []).map((v) => (
                  <div key={v} className="flex flex-col gap-1">
                    <label className="text-xs font-medium text-muted-foreground font-mono">{'{{'}{v}{'}}'}</label>
                    <input
                      type="text"
                      value={variables[v] ?? ''}
                      onChange={(e) => setVariables((prev) => ({ ...prev, [v]: e.target.value }))}
                      placeholder={`Enter ${v}…`}
                      className="h-8 w-full rounded-md border border-input bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 focus:ring-offset-background"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <button type="button" onClick={handleRender} disabled={isLoading || !allFilled}
              className={cn('flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                allFilled ? 'bg-primary text-primary-foreground hover:opacity-90' : 'bg-muted text-muted-foreground cursor-not-allowed')}>
              <Play className="h-3 w-3" />
              {isLoading ? 'Rendering…' : 'Render'}
            </button>
            {rendered && (
              <>
                <button type="button" onClick={handleCopy}
                  className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors">
                  <Copy className="h-3 w-3" /> Copy
                </button>
                <button type="button" onClick={reset}
                  className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors">
                  <RotateCcw className="h-3 w-3" /> Reset
                </button>
              </>
            )}
          </div>

          {rendered && (
            <div className="rounded-md border border-border bg-muted/40 p-3">
              <pre className="text-xs text-foreground whitespace-pre-wrap leading-relaxed font-mono overflow-x-auto max-h-64 scrollbar-thin">
                {rendered}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
