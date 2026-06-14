// services/retrieval.js

import { apiGet, apiPost } from '@/services/api';

export async function runRetrievalQuery(payload) {
  return apiPost('/retrieval/query', payload);
}

export async function getRetrievalTrace(traceId) {
  return apiGet(`/retrieval/traces/${traceId}`);
}

export async function listRetrievalTraces(params) {
  return apiGet('/retrieval/traces', params);
}

export async function getQueryRewrites(payload) {
  return apiPost('/retrieval/query-rewrite', payload);
}

export async function getRetrievalMetrics(kbId, params) {
  return apiGet(`/retrieval/${kbId}/metrics`, params);
}

export async function getGraphTraversal(payload) {
  return apiPost('/retrieval/graph-traversal', payload);
}

export async function getFederatedSources(kbId) {
  return apiGet(`/retrieval/${kbId}/federated-sources`);
}

export async function getRetrievalSettings(kbId) {
  return apiGet(`/retrieval/${kbId}/settings`);
}

export async function updateRetrievalSettings(kbId, payload) {
  return apiPost(`/retrieval/${kbId}/settings`, payload);
}