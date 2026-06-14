// services/monitoring.js

import { apiGet, apiPost } from '@/services/api';

export async function getSystemHealth() {
  return apiGet('/monitoring/health');
}

export async function getMetricsOverview(params) {
  return apiGet('/monitoring/metrics', params);
}

export async function getServiceMetrics(serviceName, params) {
  return apiGet(`/monitoring/metrics/${serviceName}`, params);
}

export async function listLogs(params) {
  return apiGet('/monitoring/logs', params);
}

export async function streamLogs(params) {
  return apiGet('/monitoring/logs/tail', params);
}

export async function listTraces(params) {
  return apiGet('/monitoring/traces', params);
}

export async function getTrace(traceId) {
  return apiGet(`/monitoring/traces/${traceId}`);
}

export async function listAlerts(params) {
  return apiGet('/monitoring/alerts', params);
}

export async function getAlert(alertId) {
  return apiGet(`/monitoring/alerts/${alertId}`);
}

export async function acknowledgeAlert(alertId) {
  return apiPost(`/monitoring/alerts/${alertId}/acknowledge`, {});
}

export async function resolveAlert(alertId) {
  return apiPost(`/monitoring/alerts/${alertId}/resolve`, {});
}

export async function getAlertRules() {
  return apiGet('/monitoring/alerts/rules');
}