// app/agents/create/page.jsx

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Bot, AlertCircle } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
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
  agent_type: AGENT_TYPES.RETRIEVAL,
  project_id: '',
  model_provider: LLM_PROVIDERS.OPENAI,
  model_name: '',
  system_prompt: '',
  max_iterations: 5,
  tools: [],
};

export default function CreateAgentPage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const { tools } = useAvailableTools();
  const [values, setValues] = useState({
    ...DEFAULT_VALUES,
    project_id: activeProjectId || '',
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Update project_id when activeProjectId becomes available
  useEffect(() => {
    if (activeProjectId) {
      setValues((prev) => ({ ...prev, project_id: activeProjectId }));
    }
  }, [activeProjectId]);

  const handleSubmit = async () => {
    const result = agentSchema.safeParse(values);

    if (!result.success) {
      const fieldErrors = {};
      result.error.issues.forEach((issue) => {
        fieldErrors[issue.path[0]] = issue.message;
      });
      setErrors(fieldErrors);

      // Show toast for project_id error since it's not in the form
      if (fieldErrors.project_id) {
        toast.error(fieldErrors.project_id);
      }
      return;
    }

    setErrors({});
    setIsSubmitting(true);
    try {
      const agent = await createAgent(values);
      toast.success('Agent created');
      router.push(ROUTES.AGENT_DETAIL(agent.id));
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Show warning if no project selected
  if (!activeProjectId) {
    return (
      <AppShell>
        <div className="mx-auto flex max-w-2xl flex-col gap-5">
          <Button variant="ghost" size="sm" className="w-fit" onClick={() => router.back()}>
            <ArrowLeft className="h-3.5 w-3.5" />
            Back
          </Button>

          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-12">
              <AlertCircle className="h-8 w-8 text-warning" />
              <div className="text-center">
                <h2 className="text-lg font-semibold">No project selected</h2>
                <p className="text-sm text-muted-foreground">
                  Please select or create a project before creating an agent.
                </p>
              </div>
              <Button onClick={() => router.push(ROUTES.PROJECTS)}>
                Go to Projects
              </Button>
            </CardContent>
          </Card>
        </div>
      </AppShell>
    );
  }

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
            <AgentConfig 
              values={values} 
              errors={errors} 
              onChange={setValues} 
              tools={tools} 
            />

            {errors.project_id && (
              <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {errors.project_id}
              </div>
            )}

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
