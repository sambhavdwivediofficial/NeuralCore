// lib/validators.js

import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  remember: z.boolean().optional(),
});

export const projectSchema = z.object({
  name: z
    .string()
    .min(2, 'Name must be at least 2 characters')
    .max(60, 'Name must be under 60 characters'),
  description: z.string().max(300, 'Description must be under 300 characters').optional(),
  defaultLlmProvider: z.string().min(1, 'Select a default LLM provider'),
  defaultEmbeddingProvider: z.string().min(1, 'Select a default embedding provider'),
});

export const knowledgeBaseSchema = z.object({
  name: z
    .string()
    .min(2, 'Name must be at least 2 characters')
    .max(60, 'Name must be under 60 characters'),
  description: z.string().max(300, 'Description must be under 300 characters').optional(),
  vectorStore: z.string().min(1, 'Select a vector store'),
  embeddingProvider: z.string().min(1, 'Select an embedding provider'),
  chunkingStrategy: z.string().min(1, 'Select a chunking strategy'),
  chunkSize: z
    .number({ invalid_type_error: 'Chunk size must be a number' })
    .min(64, 'Minimum chunk size is 64 tokens')
    .max(8192, 'Maximum chunk size is 8192 tokens'),
  chunkOverlap: z
    .number({ invalid_type_error: 'Overlap must be a number' })
    .min(0, 'Overlap cannot be negative')
    .max(1024, 'Overlap must be under 1024 tokens'),
});

export const agentSchema = z.object({
  name: z
    .string()
    .min(2, 'Name must be at least 2 characters')
    .max(60, 'Name must be under 60 characters'),
  description: z.string().max(300, 'Description must be under 300 characters').optional(),
  type: z.string().min(1, 'Select an agent type'),
  knowledgeBaseId: z.string().optional(),
  llmProvider: z.string().min(1, 'Select an LLM provider'),
  model: z.string().min(1, 'Select a model'),
  systemPrompt: z.string().max(4000, 'System prompt must be under 4000 characters').optional(),
  temperature: z
    .number({ invalid_type_error: 'Temperature must be a number' })
    .min(0, 'Minimum temperature is 0')
    .max(2, 'Maximum temperature is 2'),
  maxTokens: z
    .number({ invalid_type_error: 'Max tokens must be a number' })
    .min(1, 'Minimum is 1')
    .max(128000, 'Maximum is 128000'),
  tools: z.array(z.string()).optional(),
});

export const apiKeySchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(60, 'Name too long'),
  expiresInDays: z.number().min(0).max(365).optional(),
  scopes: z.array(z.string()).min(1, 'Select at least one scope'),
});

export const inviteUserSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  role: z.string().min(1, 'Select a role'),
});

export const llmProviderSchema = z.object({
  provider: z.string().min(1, 'Select a provider'),
  baseUrl: z.string().url('Enter a valid URL').optional().or(z.literal('')),
  apiKey: z.string().optional(),
  modelName: z.string().min(1, 'Model name is required'),
  contextWindow: z
    .number({ invalid_type_error: 'Context window must be a number' })
    .min(512, 'Minimum context window is 512 tokens')
    .optional(),
});

export const vectorStoreConfigSchema = z.object({
  provider: z.string().min(1, 'Select a provider'),
  host: z.string().min(1, 'Host is required'),
  port: z
    .number({ invalid_type_error: 'Port must be a number' })
    .min(1, 'Invalid port')
    .max(65535, 'Invalid port'),
  apiKey: z.string().optional(),
  collectionPrefix: z.string().optional(),
  useTls: z.boolean().optional(),
});

export const retrievalSettingsSchema = z.object({
  strategy: z.string().min(1, 'Select a retrieval strategy'),
  topK: z
    .number({ invalid_type_error: 'Top K must be a number' })
    .min(1, 'Minimum is 1')
    .max(100, 'Maximum is 100'),
  vectorWeight: z.number().min(0).max(1),
  bm25Weight: z.number().min(0).max(1),
  rerankEnabled: z.boolean(),
  rerankStrategy: z.string().optional(),
  similarityThreshold: z.number().min(0).max(1),
});

export const queryRewriteSchema = z.object({
  enabled: z.boolean(),
  strategies: z.array(z.string()),
});

export const securitySettingsSchema = z.object({
  mfaRequired: z.boolean(),
  sessionTimeoutMinutes: z
    .number({ invalid_type_error: 'Session timeout must be a number' })
    .min(5, 'Minimum is 5 minutes')
    .max(1440, 'Maximum is 1440 minutes'),
  ipAllowlist: z.string().optional(),
});

export function getFieldError(errors, name) {
  return errors?.[name]?.message;
}