// services/analytics.js

import { apiGet } from '@/services/api';

export async function getDashboardStats(params) {
  return apiGet('/analytics/dashboard', params);
}

export async function getUsageOverTime(params) {
  return apiGet('/analytics/usage', params);
}

export async function getCostBreakdown(params) {
  return apiGet('/analytics/costs', params);
}

export async function getTokenUsage(params) {
  return apiGet('/analytics/tokens', params);
}

export async function getActivityFeed(params) {
  return apiGet('/analytics/activity', params);
}

export async function getModelUsageBreakdown(params) {
  return apiGet('/analytics/models', params);
}

export async function getLatencyDistribution(params) {
  return apiGet('/analytics/latency', params);
}