// services/knowledgebases.js

import { apiGet, apiPost, apiPatch, apiDelete, apiUpload } from '@/services/api';

export async function listKnowledgeBases(params) {
  return apiGet('/knowledge-bases', params);
}

export async function getKnowledgeBase(kbId) {
  return apiGet(`/knowledge-bases/${kbId}`);
}

export async function createKnowledgeBase(payload) {
  return apiPost('/knowledge-bases', payload);
}

export async function updateKnowledgeBase(kbId, payload) {
  return apiPatch(`/knowledge-bases/${kbId}`, payload);
}

export async function deleteKnowledgeBase(kbId) {
  return apiDelete(`/knowledge-bases/${kbId}`);
}

export async function listDocuments(kbId, params) {
  return apiGet(`/knowledge-bases/${kbId}/documents`, params);
}

export async function getDocument(kbId, documentId) {
  return apiGet(`/knowledge-bases/${kbId}/documents/${documentId}`);
}

export async function uploadDocument(kbId, formData, onUploadProgress) {
  return apiUpload(`/knowledge-bases/${kbId}/documents`, formData, onUploadProgress);
}

export async function deleteDocument(kbId, documentId) {
  return apiDelete(`/knowledge-bases/${kbId}/documents/${documentId}`);
}

export async function reprocessDocument(kbId, documentId) {
  return apiPost(`/knowledge-bases/${kbId}/documents/${documentId}/reprocess`, {});
}

export async function getDocumentChunks(kbId, documentId, params) {
  return apiGet(`/knowledge-bases/${kbId}/documents/${documentId}/chunks`, params);
}

export async function listChunks(kbId, params) {
  return apiGet(`/knowledge-bases/${kbId}/chunks`, params);
}

export async function getChunk(kbId, chunkId) {
  return apiGet(`/knowledge-bases/${kbId}/chunks/${chunkId}`);
}

export async function updateChunk(kbId, chunkId, payload) {
  return apiPatch(`/knowledge-bases/${kbId}/chunks/${chunkId}`, payload);
}

export async function deleteChunk(kbId, chunkId) {
  return apiDelete(`/knowledge-bases/${kbId}/chunks/${chunkId}`);
}

export async function getKnowledgeBaseStats(kbId) {
  return apiGet(`/knowledge-bases/${kbId}/stats`);
}

export async function getIngestionSources() {
  return apiGet('/knowledge-bases/sources');
}

export async function connectIngestionSource(kbId, payload) {
  return apiPost(`/knowledge-bases/${kbId}/sources`, payload);
}

export async function getChunkingStrategies() {
  return apiGet('/knowledge-bases/chunking-strategies');
}