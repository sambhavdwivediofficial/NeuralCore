// services/projects.js

import { apiGet, apiPost, apiPatch, apiDelete } from '@/services/api';

export async function listProjects(params) {
  return apiGet('/projects', params);
}

export async function getProject(projectId) {
  return apiGet(`/projects/${projectId}`);
}

export async function createProject(payload) {
  return apiPost('/projects', payload);
}

export async function updateProject(projectId, payload) {
  return apiPatch(`/projects/${projectId}`, payload);
}

export async function deleteProject(projectId) {
  return apiDelete(`/projects/${projectId}`);
}

export async function getProjectAnalytics(projectId, params) {
  return apiGet(`/projects/${projectId}/analytics`, params);
}

export async function getProjectUsage(projectId, params) {
  return apiGet(`/projects/${projectId}/usage`, params);
}

export async function getProjectMembers(projectId) {
  return apiGet(`/projects/${projectId}/members`);
}

export async function updateProjectMember(projectId, userId, payload) {
  return apiPatch(`/projects/${projectId}/members/${userId}`, payload);
}

export async function removeProjectMember(projectId, userId) {
  return apiDelete(`/projects/${projectId}/members/${userId}`);
}

export async function getProjectSettings(projectId) {
  return apiGet(`/projects/${projectId}/settings`);
}

export async function updateProjectSettings(projectId, payload) {
  return apiPatch(`/projects/${projectId}/settings`, payload);
}