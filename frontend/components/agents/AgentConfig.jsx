// components/agents/AgentConfig.jsx

'use client';

import { Label } from '@/components/common/Label';
import { Input } from '@/components/common/Input';
import { Textarea } from '@/components/common/Textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { Checkbox } from '@/components/common/Checkbox';
import { AGENT_TYPES, AGENT_TYPE_LABELS, LLM_PROVIDERS, LLM_PROVIDER_LABELS } from '@/lib/constants';

export function AgentConfig({ values, errors, onChange, tools = [] }) {
  const setField = (field, value) => onChange({ ...values, [field]: value });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="agent-name">Agent name</Label>
        <Input
          id="agent-name"
          value={values.name}
          onChange={(e) => setField('name', e.target.value)}
          placeholder="Research Assistant"
        />
        {errors?.name ? <p className="text-xs text-destructive">{errors.name}</p> : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="agent-description">Description</Label>
        <Textarea
          id="agent-description"
          rows={2}
          value={values.description}
          onChange={(e) => setField('description', e.target.value)}
          placeholder="What does this agent do?"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label>Agent type</Label>
          <Select value={values.type} onValueChange={(value) => setField('type', value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.values(AGENT_TYPES).map((type) => (
                <SelectItem key={type} value={type}>
                  {AGENT_TYPE_LABELS[type]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors?.type ? <p className="text-xs text-destructive">{errors.type}</p> : null}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>LLM provider</Label>
          <Select value={values.llmProvider} onValueChange={(value) => setField('llmProvider', value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.values(LLM_PROVIDERS).map((provider) => (
                <SelectItem key={provider} value={provider}>
                  {LLM_PROVIDER_LABELS[provider]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors?.llmProvider ? <p className="text-xs text-destructive">{errors.llmProvider}</p> : null}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="agent-model">Model</Label>
        <Input
          id="agent-model"
          value={values.model}
          onChange={(e) => setField('model', e.target.value)}
          placeholder="gpt-4o, claude-sonnet-4-6, llama-3-70b..."
        />
        {errors?.model ? <p className="text-xs text-destructive">{errors.model}</p> : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="agent-system-prompt">System prompt</Label>
        <Textarea
          id="agent-system-prompt"
          rows={5}
          value={values.systemPrompt}
          onChange={(e) => setField('systemPrompt', e.target.value)}
          placeholder="You are a helpful research assistant that..."
          className="font-mono text-xs"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="agent-temperature">Temperature</Label>
          <Input
            id="agent-temperature"
            type="number"
            step="0.1"
            min="0"
            max="2"
            value={values.temperature}
            onChange={(e) => setField('temperature', Number(e.target.value))}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="agent-max-tokens">Max tokens</Label>
          <Input
            id="agent-max-tokens"
            type="number"
            min="1"
            value={values.maxTokens}
            onChange={(e) => setField('maxTokens', Number(e.target.value))}
          />
        </div>
      </div>

      {tools.length > 0 ? (
        <div className="flex flex-col gap-2">
          <Label>Available tools</Label>
          <div className="grid grid-cols-2 gap-2 rounded-md border border-border p-3">
            {tools.map((tool) => {
              const checked = values.tools?.includes(tool.id);
              return (
                <label key={tool.id} className="flex cursor-pointer items-center gap-2 text-sm">
                  <Checkbox
                    checked={checked}
                    onCheckedChange={(value) => {
                      const next = new Set(values.tools || []);
                      if (value) next.add(tool.id);
                      else next.delete(tool.id);
                      setField('tools', Array.from(next));
                    }}
                  />
                  {tool.name}
                </label>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
