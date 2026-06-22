// frontend/lib/validators.js

import { z } from 'zod';

const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
  .regex(/[0-9]/, 'Must contain at least one number')
  .regex(/[^A-Za-z0-9]/, 'Must contain at least one special character');

export const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
  remember: z.boolean().optional(),
});

export const signupSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters').max(80),
    email: z.string().email('Enter a valid email address'),
    password: passwordSchema,
    confirmPassword: z.string(),
    organization_name: z.string().min(2, 'Organization name is required').max(80).optional().or(z.literal('')),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export const forgotPasswordSchema = z.object({
  email: z.string().email('Enter a valid email address'),
});

export const resetPasswordSchema = z
  .object({
    new_password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((d) => d.new_password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export const acceptInviteSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters').max(80),
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export const mfaCodeSchema = z.object({
  code: z
    .string()
    .length(6, 'Code must be 6 digits')
    .regex(/^\d{6}$/, 'Code must be 6 digits'),
});

export const profileSchema = z.object({
  name: z.string().min(2).max(80).optional(),
  avatar_url: z.string().url('Enter a valid URL').optional().or(z.literal('')),
  bio: z.string().max(300).optional(),
});

export const securitySettingsSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export const apiKeySchema = z.object({
  name: z.string().min(1, 'Name is required').max(60),
  scope: z.enum(['read', 'write', 'admin']),
});

export const inviteUserSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  role: z.enum(['admin', 'developer', 'viewer']),
});

export const projectSchema = z.object({
  name: z.string().min(1, 'Name is required').max(80),
  description: z.string().max(500).optional(),
});

export const organizationSchema = z.object({
  name: z.string().min(2, 'Organization name is required').max(80),
  billing_email: z.string().email('Enter a valid email').optional().or(z.literal('')),
});

export const knowledgeBaseSchema = z.object({
  name: z.string().min(1, 'Name is required').max(80),
  project_id: z.string().min(1, 'Select a project'),
  description: z.string().max(500).optional(),
  embedding_provider: z.string().optional(),
  embedding_model: z.string().optional(),
  chunking_strategy: z.string().optional(),
  chunk_size: z.coerce.number().min(64).max(8192).optional(),
  chunk_overlap: z.coerce.number().min(0).max(512).optional(),
  vector_db_backend: z.string().optional(),
});

export const agentSchema = z.object({
  name: z.string().min(1, 'Name is required').max(80),
  agent_type: z.string().min(1, 'Select an agent type'),
  project_id: z.string().min(1, 'Select a project'),
  description: z.string().max(500).optional(),
  system_prompt: z.string().max(8000).optional(),
  model_provider: z.string().optional(),
  model_name: z.string().optional(),
  max_iterations: z.coerce.number().min(1).max(100).optional(),
  tools: z.array(z.string()).optional(),
});

export const workflowSchema = z.object({
  name: z.string().min(1, 'Name is required').max(80),
  project_id: z.string().min(1, 'Select a project'),
  description: z.string().max(500).optional(),
  template: z.string().optional(),
});

export const datasetSchema = z.object({
  name: z.string().min(1, 'Name is required').max(80),
  project_id: z.string().min(1, 'Select a project'),
  format: z.enum(['alpaca', 'sharegpt', 'openai', 'custom']).optional(),
  description: z.string().max(500).optional(),
});

export const onboardingSchema = z.object({
  organization_name: z.string().min(2, 'Organization name is required').max(80),
  billing_email: z.string().email('Enter a valid email').optional().or(z.literal('')),
});

export const retrievalQuerySchema = z.object({
  query: z.string().min(1, 'Enter a query'),
  knowledge_base_id: z.string().min(1, 'Select a knowledge base'),
  strategy: z.string().optional(),
  top_k: z.coerce.number().min(1).max(100).optional(),
  use_reranking: z.boolean().optional(),
  use_graph: z.boolean().optional(),
});

export const pipelineRunSchema = z.object({
  query: z.string().min(1, 'Enter a question'),
  knowledge_base_id: z.string().min(1, 'Select a knowledge base'),
  pipeline_type: z.enum(['rag', 'agentic_rag', 'graphrag']).optional(),
});
