// services/embeddings.js

import { apiGet, apiPost } from '@/services/api';

export async function listEmbeddingProviders() {
  return apiGet('/embeddings/providers');
}

export async function getEmbeddingProvider(providerId) {
  return apiGet(`/embeddings/providers/${providerId}`);
}

export async function testEmbeddingProvider(payload) {
  return apiPost('/embeddings/providers/test', payload);
}

export async function generateEmbedding(payload) {
  return apiPost('/embeddings/generate', payload);
}

export async function getEmbeddingVisualization(kbId, params) {
  return apiGet(`/embeddings/${kbId}/visualization`, params);
}

export async function getEmbeddingCacheStats() {
  return apiGet('/embeddings/cache/stats');
}

export async function clearEmbeddingCache() {
  return apiPost('/embeddings/cache/clear', {});
}