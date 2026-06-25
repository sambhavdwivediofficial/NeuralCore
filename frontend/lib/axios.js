// lib/axios.js

import axios from 'axios';
import { API_BASE_URL, API_PREFIX, AUTH_COOKIE_NAME } from '@/lib/constants';
import { PUBLIC_ROUTES, PUBLIC_ROUTE_PREFIXES } from '@/lib/routes';

function getCookie(name) {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getCookie(AUTH_COOKIE_NAME);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise = null;

function isPublicPath(pathname) {
  if (PUBLIC_ROUTES.includes(pathname)) return true;
  if (PUBLIC_ROUTE_PREFIXES.some((p) => pathname.startsWith(p))) return true;
  return false;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (!refreshPromise) {
        refreshPromise = axios
          .post(`${API_BASE_URL}${API_PREFIX}/auth/refresh`, {}, { withCredentials: true })
          .then((response) => {
            refreshPromise = null;
            return response.data;
          })
          .catch((refreshError) => {
            refreshPromise = null;
            if (typeof window !== 'undefined') {
              const currentPath = window.location.pathname;
              if (!isPublicPath(currentPath)) {
                window.location.href = '/';
              }
            }
            throw refreshError;
          });
      }

      try {
        await refreshPromise;
        return apiClient(originalRequest);
      } catch (refreshError) {
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export function getErrorMessage(error) {
  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error?.response?.data?.message) {
    return error.response.data.message;
  }
  if (error?.message) {
    return error.message;
  }
  return 'Something went wrong. Please try again.';
}

export default apiClient;
