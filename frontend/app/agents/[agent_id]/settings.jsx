// app/agents/[agent_id]/settings.jsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Trash2 } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from '@/components/common/Card';
import { Separator } from '@/components/common/Separator';
import { PageLoader } from '@/components/common/Loader';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
} from '@/components/common/Modal';
import { AgentConfig } from '@/components/agents/AgentConfig';
import { useAgent, useAvailableTools } from '@/hooks/useAgents';
import { updateAgent, deleteAgent, clearAgentMemory } from '@/services/agents';
import { agentSchema } from '@/lib/validators';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';

const MEMORY_LAYERS = ['short_term', 'long_term', 'semantic', 'episodic', 'session'];

export default function AgentSettingsPage({ params }) {
  const router = useRouter();
  const { agent, isLoading, refresh } = useAgent(params.agent_id);
  const { tools } = useAvailableTools();
  const [values, setValues] = useState(null);
  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  useEffect(() => {
    if (agent) {
      setValues({
        name: agent.name,
        description: agent.description || '',
        type: agent.type,
        llmProvider: agent.llm_provider,
        model: agent.model,
        systemPrompt: agent.system_prompt || '',
        temperature: agent.temperature,
        maxTokens: agent.max_tokens,
        tools: agent.tools || [],
      });
    }
  }, [agent]);

  const handleSave = async () => {
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
    setIsSaving(true);
    try {
      await updateAgent(params.agent_id, {
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
      toast.success('Agent settings saved');
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deleteAgent(params.agent_id);
      toast.success('Agent deleted');
      router.push(ROUTES.AGENTS);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsDeleting(false);
    }
  };

  const handleClearMemory = async (layer) => {
    try {
      await clearAgentMemory(params.agent_id, layer);
      toast.success(`${layer.replace('_', ' ')} memory cleared`);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  if (isLoading || !values) {
    return (
      <AppShell>
        <PageLoader label="Loading settings" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          onClick={() => router.push(ROUTES.AGENT_DETAIL(params.agent_id))}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          {agent?.name}
        </Button>

        <Card>
          <CardHeader>
            <CardTitle>Agent configuration</CardTitle>
            <CardDescription>Update behavior, model, and available tools</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <AgentConfig values={values} errors={errors} onChange={setValues} tools={tools} />
            <div className="flex justify-end pt-2">
              <Button onClick={handleSave} isLoading={isSaving}>
                Save changes
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Memory layers</CardTitle>
            <CardDescription>Clear stored context for this agent by memory layer</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {MEMORY_LAYERS.map((layer) => (
              <Button
                key={layer}
                variant="outline"
                size="sm"
                onClick={() => handleClearMemory(layer)}
                className="capitalize"
              >
                Clear {layer.replace('_', ' ')}
              </Button>
            ))}
          </CardContent>
        </Card>

        <Card className="border-destructive/30">
          <CardHeader>
            <CardTitle className="text-destructive">Danger zone</CardTitle>
            <CardDescription>Deleting this agent removes all run history permanently.</CardDescription>
          </CardHeader>
          <Separator />
          <CardFooter className="justify-end pt-4">
            <Button variant="destructive" onClick={() => setShowDeleteModal(true)}>
              <Trash2 className="h-3.5 w-3.5" />
              Delete agent
            </Button>
          </CardFooter>
        </Card>
      </div>

      <Modal open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Delete agent</ModalTitle>
            <ModalDescription>
              This will permanently delete &quot;{agent?.name}&quot; and its run history. This action
              cannot be undone.
            </ModalDescription>
          </ModalHeader>
          <ModalFooter>
            <Button variant="outline" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isDeleting} onClick={handleDelete}>
              Delete agent
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </AppShell>
  );
}
