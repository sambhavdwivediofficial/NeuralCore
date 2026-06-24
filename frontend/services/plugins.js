// frontend/services/plugins.js

import { apiGet } from '@/services/api';

export async function listPlugins() {
  return apiGet('/plugins');
}
