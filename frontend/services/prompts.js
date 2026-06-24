// frontend/services/prompts.js

import { apiGet, apiPost } from '@/services/api';

export async function listPromptTemplates() {
  return apiGet('/prompts');
}

export async function renderPrompt(payload) {
  return apiPost('/prompts/render', payload);
}
