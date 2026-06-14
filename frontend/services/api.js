// services/api.js

import apiClient from '@/lib/axios';
import { buildQueryString } from '@/lib/utils';

export async function apiGet(path, params) {
  const query = params ? buildQueryString(params) : '';
  const response = await apiClient.get(`${path}${query}`);
  return response.data;
}

export async function apiPost(path, body) {
  const response = await apiClient.post(path, body);
  return response.data;
}

export async function apiPut(path, body) {
  const response = await apiClient.put(path, body);
  return response.data;
}

export async function apiPatch(path, body) {
  const response = await apiClient.patch(path, body);
  return response.data;
}

export async function apiDelete(path) {
  const response = await apiClient.delete(path);
  return response.data;
}

export async function apiUpload(path, formData, onUploadProgress) {
  const response = await apiClient.post(path, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  });
  return response.data;
}

export function createEventStream(path, onMessage, onError, onComplete) {
  const controller = new AbortController();

  const baseUrl = apiClient.defaults.baseURL;

  fetch(`${baseUrl}${path}`, {
    method: 'GET',
    headers: { Accept: 'text/event-stream' },
    credentials: 'include',
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.body) throw new Error('Stream not supported');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop();
        lines.forEach((chunk) => {
          const dataLine = chunk.split('\n').find((line) => line.startsWith('data:'));
          if (!dataLine) return;
          const raw = dataLine.replace('data:', '').trim();
          if (raw === '[DONE]') {
            onComplete?.();
            return;
          }
          try {
            onMessage(JSON.parse(raw));
          } catch (error) {
            onMessage(raw);
          }
        });
      }
      onComplete?.();
    })
    .catch((error) => {
      if (error.name !== 'AbortError') {
        onError?.(error);
      }
    });

  return () => controller.abort();
}