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