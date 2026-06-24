// frontend/services/pipelines.js

import { apiGet, apiPost } from '@/services/api';

export async function listPipelines() {
  return apiGet('/pipelines');
}

export async function runPipeline(payload) {
  return apiPost('/pipelines/run', payload);
}
