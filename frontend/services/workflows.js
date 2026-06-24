// frontend/services/workflows.js

import { apiGet, apiPost, apiPatch, apiDelete } from '@/services/api';

export async function listWorkflows(params = {}) {
  return apiGet('/workflows', { params });
}

export async function getWorkflow(workflowId) {
  return apiGet(`/workflows/${workflowId}`);
}

export async function createWorkflow(payload) {
  return apiPost('/workflows', payload);
}

export async function updateWorkflow(workflowId, payload) {
  return apiPatch(`/workflows/${workflowId}`, payload);
}

export async function deleteWorkflow(workflowId) {
  return apiDelete(`/workflows/${workflowId}`);
}

export async function runWorkflow(workflowId, payload = {}) {
  return apiPost(`/workflows/${workflowId}/run`, payload);
}

export async function listWorkflowRuns(workflowId, params = {}) {
  return apiGet(`/workflows/${workflowId}/runs`, { params });
}

export async function getWorkflowRun(workflowId, runId) {
  return apiGet(`/workflows/${workflowId}/runs/${runId}`);
}
