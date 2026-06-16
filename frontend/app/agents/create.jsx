// app/agents/create.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Bot } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { AgentConfig } from '@/components/agents/AgentConfig';
import { useAvailableTools } from '@/hooks/useAgents';
import { useProjectContext } from '@/context/ProjectContext';
import { createAgent } from '@/services/agents';
import { agentSchema } from '@/lib/validators';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { AGENT_TYPES, LLM_PROVIDERS } from '@/lib/constants';

const DEFAULT_VALUES = {
  name: '',
  description: '',
  type: AGENT_TYPES.RETRIEVAL,
  llmProvider: LLM_PROVIDERS.OPENAI,
  model: '',
  systemPrompt: '',
  temperature: 0.7,
  maxTokens: 4096,
  tools: [],
};

export default function CreateAgentPage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const { tools } = useAvailableTools();
  const [values, setValues] = useState(DEFAULT_VALUES);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    const result = agentSchema.safeParse(values);

    if (!result.success) {
      const fieldErrors = {};
      result.error.issues.forEach((issue) => {
        fieldErrors[issue.path[0]] = issue.message;
      });
      setErrors(fieldErrors);
      return;
    }

    setErrors({});
    setIsSubmitting(true);
    try {
      const agent = await createAgent({
        project_id: activeProjectId,
        name: values.name,
        description: values.description,
        type: values.type,
        llm_provider: values.llmProvider,
        model: values.model,
        system_prompt: values.systemPrompt,
        temperature: values.temperature,
        max_tokens: values.maxTokens,
        tools: values.tools,
      });
      toast.success('Agent created');
      router.push(ROUTES.AGENT_DETAIL(agent.id));
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => router.back()}>
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </Button>

        <Card>
          <CardHeader>
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Bot className="h-4 w-4" />
            </div>
            <CardTitle className="mt-2">Create a new agent</CardTitle>
            <CardDescription>
              Configure the model, behavior, and tools this agent has access to.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <AgentConfig values={values} errors={errors} onChange={setValues} tools={tools} />
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => router.back()}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} isLoading={isSubmitting}>
                Create agent
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
