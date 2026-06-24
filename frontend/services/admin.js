// frontend/services/admin.js

import { apiGet } from '@/services/api';

export async function getPlatformStats() {
  return apiGet('/admin/stats');
}

export async function listAllOrganizations() {
  return apiGet('/admin/organizations');
}
