// frontend/services/auth.js

import { apiGet, apiPost, apiPatch } from '@/services/api';

export async function login(credentials) {
  return apiPost('/auth/login', credentials);
}

export async function signup(payload) {
  return apiPost('/auth/signup', payload);
}

export async function logout() {
  return apiPost('/auth/logout', {});
}

export async function refreshSession() {
  return apiPost('/auth/refresh', {});
}

export async function forgotPassword(email) {
  return apiPost('/auth/forgot-password', { email });
}

export async function resetPassword(token, new_password) {
  return apiPost('/auth/reset-password', { token, new_password });
}

export async function requestVerifyEmail() {
  return apiPost('/auth/verify-email/request', {});
}

export async function verifyEmail(token) {
  return apiPost('/auth/verify-email', { token });
}

export async function getInvite(token) {
  return apiGet(`/auth/invite/${token}`);
}

export async function acceptInvite(payload) {
  return apiPost('/auth/accept-invite', payload);
}

export async function completeMfaChallenge(challenge_token, code) {
  return apiPost('/auth/mfa/challenge', { challenge_token, code });
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

export async function verifyMfa(code) {
  return apiPost('/auth/mfa/verify', { code });
}

export async function disableMfa() {
  return apiPost('/auth/mfa/disable', {});
}

export async function toggleMfa(enabled) {
  return apiPost('/auth/mfa/toggle', { enabled });
}

export async function listSessions() {
  return apiGet('/auth/sessions');
}

export async function revokeSession(sessionId) {
  return apiPost(`/auth/sessions/${sessionId}/revoke`, {});
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
