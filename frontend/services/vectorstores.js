// services/vectorstores.js

import { apiGet, apiPost, apiPatch, apiDelete } from '@/services/api';

export async function listVectorStores() {
  return apiGet('/vector-stores');
}

export async function getVectorStore(storeId) {
  return apiGet(`/vector-stores/${storeId}`);
}

export async function createVectorStore(payload) {
  return apiPost('/vector-stores', payload);
}

export async function updateVectorStore(storeId, payload) {
  return apiPatch(`/vector-stores/${storeId}`, payload);
}

export async function deleteVectorStore(storeId) {
  return apiDelete(`/vector-stores/${storeId}`);
}

export async function testVectorStoreConnection(payload) {
  return apiPost('/vector-stores/test-connection', payload);
}

export async function getVectorStoreCollections(storeId) {
  return apiGet(`/vector-stores/${storeId}/collections`);
}

export async function getVectorStoreMetrics(storeId, params) {
  return apiGet(`/vector-stores/${storeId}/metrics`, params);
}

export async function getQdrantStatus(storeId) {
  return apiGet(`/vector-stores/${storeId}/qdrant/status`);
}

export async function getMilvusStatus(storeId) {
  return apiGet(`/vector-stores/${storeId}/milvus/status`);
}

export async function getPgVectorStatus(storeId) {
  return apiGet(`/vector-stores/${storeId}/pgvector/status`);
}

export async function rebuildVectorIndex(storeId, collectionName) {
  return apiPost(`/vector-stores/${storeId}/collections/${collectionName}/rebuild`, {});
}

export async function snapshotVectorStore(storeId) {
  return apiPost(`/vector-stores/${storeId}/snapshot`, {});
}