// hooks/useKnowledgeBases.js

import { useCallback, useEffect, useState } from 'react';
import * as kbService from '@/services/knowledgebases';
import { getErrorMessage } from '@/lib/axios';
import { POLLING_INTERVALS, DOCUMENT_STATUS } from '@/lib/constants';

export function useKnowledgeBases(params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchKbs = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await kbService.listKnowledgeBases(params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchKbs();
  }, [fetchKbs]);

  return {
    knowledgeBases: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchKbs,
  };
}

export function useKnowledgeBase(kbId) {
  const [knowledgeBase, setKnowledgeBase] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchKb = useCallback(async () => {
    if (!kbId) return;
    setIsLoading(true);
    try {
      const result = await kbService.getKnowledgeBase(kbId);
      setKnowledgeBase(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [kbId]);

  useEffect(() => {
    fetchKb();
  }, [fetchKb]);

  return {
    knowledgeBase,
    isLoading,
    error,
    refresh: fetchKb,
  };
}

export function useDocuments(kbId, params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDocuments = useCallback(async () => {
    if (!kbId) return;
    setIsLoading(true);
    try {
      const result = await kbService.listDocuments(kbId, params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [kbId, JSON.stringify(params)]);

  useEffect(() => {
    fetchDocuments();

    const hasProcessing = data?.items?.some(
      (doc) => doc.status === DOCUMENT_STATUS.PROCESSING || doc.status === DOCUMENT_STATUS.QUEUED
    );

    if (!hasProcessing) return;

    const interval = setInterval(fetchDocuments, POLLING_INTERVALS.DOCUMENT_STATUS);
    return () => clearInterval(interval);
  }, [fetchDocuments]);

  return {
    documents: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchDocuments,
  };
}

export function useChunks(kbId, params) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchChunks = useCallback(async () => {
    if (!kbId) return;
    setIsLoading(true);
    try {
      const result = await kbService.listChunks(kbId, params);
      setData(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [kbId, JSON.stringify(params)]);

  useEffect(() => {
    fetchChunks();
  }, [fetchChunks]);

  return {
    chunks: data?.items || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: fetchChunks,
  };
}

export function useKnowledgeBaseStats(kbId) {
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = useCallback(async () => {
    if (!kbId) return;
    setIsLoading(true);
    try {
      const result = await kbService.getKnowledgeBaseStats(kbId);
      setStats(result);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [kbId]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return {
    stats,
    isLoading,
    error,
    refresh: fetchStats,
  };
}