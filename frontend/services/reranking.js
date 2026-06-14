// services/reranking.js

import { apiGet, apiPost } from '@/services/api';

export async function listRerankStrategies() {
  return apiGet('/reranking/strategies');
}

export async function runRerank(payload) {
  return apiPost('/reranking/run', payload);
}

export async function compareRerankStrategies(payload) {
  return apiPost('/reranking/compare', payload);
}

export async function getRerankMetrics(kbId, params) {
  return apiGet(`/reranking/${kbId}/metrics`, params);
}