// frontend/services/datasets.js

import { apiGet, apiPost, apiPatch, apiDelete } from '@/services/api';

export async function listDatasets(params = {}) {
  return apiGet('/datasets', { params });
}

export async function getDataset(datasetId) {
  return apiGet(`/datasets/${datasetId}`);
}

export async function createDataset(payload) {
  return apiPost('/datasets', payload);
}

export async function updateDataset(datasetId, payload) {
  return apiPatch(`/datasets/${datasetId}`, payload);
}

export async function deleteDataset(datasetId) {
  return apiDelete(`/datasets/${datasetId}`);
}
