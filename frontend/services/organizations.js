// frontend/services/organizations.js

import { apiGet, apiPost, apiPatch } from '@/services/api';

export async function listOrganizations() {
  return apiGet('/organizations');
}

export async function getOrganization(orgId) {
  return apiGet(`/organizations/${orgId}`);
}

export async function createOrganization(payload) {
  return apiPost('/organizations', payload);
}

export async function updateOrganization(orgId, payload) {
  return apiPatch(`/organizations/${orgId}`, payload);
}
