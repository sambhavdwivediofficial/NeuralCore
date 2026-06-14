// hooks/useMonitoring.js

import { useCallback, useEffect, useState } from 'react';
import * as monitoringService from '@/services/monitoring';
import { getErrorMessage } from '@/lib/axios';
import { POLLING_INTERVALS } from '@/lib/constants';

export function useSystemHealth() {
  const [health, setHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await monitoringService.getSystemHealth();
      setHealth(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, POLLING_INTERVALS.METRICS);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  return { health, isLoading, error, refresh: fetchHealth };
}

export function useMetricsOverview(params) {
  const [metrics, setMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await monitoringService.getMetricsOverview(params);
      setMetrics(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, POLLING_INTERVALS.METRICS);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  return { metrics, isLoading, error, refresh: fetchMetrics };
}

export function useLogs(params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await monitoringService.listLogs(params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, POLLING_INTERVALS.LOGS);
    return () => clearInterval(interval);
  }, [fetchLogs]);

  return {
    logs: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchLogs,
  };
}

export function useTraces(params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTraces = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await monitoringService.listTraces(params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  return {
    traces: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchTraces,
  };
}

export function useAlerts(params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAlerts = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await monitoringService.listAlerts(params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, POLLING_INTERVALS.ALERTS);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  return {
    alerts: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchAlerts,
  };
}