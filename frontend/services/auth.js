// services/auth.js

import { apiGet, apiPost, apiPatch } from '@/services/api';

export async function login(credentials) {
  return apiPost('/auth/login', credentials);
}

export async function logout() {
  return apiPost('/auth/logout', {});
}

export async function refreshSession() {
  return apiPost('/auth/refresh', {});
}

export async function getCurrentUser() {
  return apiGet('/auth/me');
}

export async function updateProfile(payload) {
  return apiPatch('/auth/me', payload);
}

export async function changePassword(payload) {
  return apiPost('/auth/change-password', payload);
}

export async function enableMfa() {
  return apiPost('/auth/mfa/enable', {});
}

export async function verifyMfa(payload) {
  return apiPost('/auth/mfa/verify', payload);
}

export async function disableMfa() {
  return apiPost('/auth/mfa/disable', {});
}

export async function listSessions() {
  return apiGet('/auth/sessions');
}

export async function revokeSession(sessionId) {
  return apiPost(`/auth/sessions/${sessionId}/revoke`, {});
}

export async function toggleTwoFactor(enabled) {
  return apiPost('/auth/mfa/toggle', { enabled });
}

export async function listApiKeys() {
  return apiGet('/auth/api-keys');
}

export async function createApiKey(payload) {
  return apiPost('/auth/api-keys', payload);
}

export async function revokeApiKey(keyId) {
  return apiPost(`/auth/api-keys/${keyId}/revoke`, {});
}

export async function listTeamMembers() {
  return apiGet('/auth/users');
}

export async function inviteUser(payload) {
  return apiPost('/auth/users/invite', payload);
}

export async function updateUserRole(userId, role) {
  return apiPatch(`/auth/users/${userId}`, { role });
}

export async function removeUser(userId) {
  return apiPost(`/auth/users/${userId}/remove`, {});
}