// frontend/services/workspaces.js

import { apiGet } from '@/services/api';

export async function listWorkspaces() {
  return apiGet('/workspaces');
}
