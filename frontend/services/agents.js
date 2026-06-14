// services/agents.js

import { apiGet, apiPost, apiPatch, apiDelete, createEventStream } from '@/services/api';

export async function listAgents(params) {
  return apiGet('/agents', params);
}

export async function getAgent(agentId) {
  return apiGet(`/agents/${agentId}`);
}

export async function createAgent(payload) {
  return apiPost('/agents', payload);
}

export async function updateAgent(agentId, payload) {
  return apiPatch(`/agents/${agentId}`, payload);
}

export async function deleteAgent(agentId) {
  return apiDelete(`/agents/${agentId}`);
}

export async function getAgentSettings(agentId) {
  return apiGet(`/agents/${agentId}/settings`);
}

export async function updateAgentSettings(agentId, payload) {
  return apiPatch(`/agents/${agentId}/settings`, payload);
}

export async function runAgent(agentId, payload) {
  return apiPost(`/agents/${agentId}/run`, payload);
}

export async function pauseAgent(agentId) {
  return apiPost(`/agents/${agentId}/pause`, {});
}

export async function resumeAgent(agentId) {
  return apiPost(`/agents/${agentId}/resume`, {});
}

export async function stopAgent(agentId) {
  return apiPost(`/agents/${agentId}/stop`, {});
}

export async function getAgentRuns(agentId, params) {
  return apiGet(`/agents/${agentId}/runs`, params);
}

export async function getAgentRun(agentId, runId) {
  return apiGet(`/agents/${agentId}/runs/${runId}`);
}

export async function getAgentLogs(agentId, runId, params) {
  return apiGet(`/agents/${agentId}/runs/${runId}/logs`, params);
}

export function streamAgentRun(agentId, runId, onMessage, onError, onComplete) {
  return createEventStream(`/agents/${agentId}/runs/${runId}/stream`, onMessage, onError, onComplete);
}

export async function getAgentMemory(agentId, params) {
  return apiGet(`/agents/${agentId}/memory`, params);
}

export async function clearAgentMemory(agentId, layer) {
  return apiDelete(`/agents/${agentId}/memory/${layer}`);
}

export async function getAvailableTools() {
  return apiGet('/agents/tools');
}