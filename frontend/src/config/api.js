/**
 * Axios API client configuration
 * Handles requests, interceptors, and error handling
 */

import axios from 'axios';

// ═══════════════════════════════════════════════════════════════
// CONFIGURATION (Vite-native)
// ═══════════════════════════════════════════════════════════════

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api';

const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT || 30000);
const DEBUG = (import.meta.env.VITE_DEBUG || 'true') === 'true';

// Log configuration (for debugging)
if (DEBUG) {
  console.log('🔧 API Config:', { API_BASE_URL, API_TIMEOUT });
}

// ═══════════════════════════════════════════════════════════════
// CREATE API CLIENT
// ═══════════════════════════════════════════════════════════════

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// (keep the rest of your file exactly the same)
export default apiClient;

export const apiGet = async (url, config = {}) => {
  const response = await apiClient.get(url, config);
  return response.data;
};

export const apiPost = async (url, data = {}, config = {}) => {
  const response = await apiClient.post(url, data, config);
  return response.data;
};

export const apiPatch = async (url, data = {}, config = {}) => {
  const response = await apiClient.patch(url, data, config);
  return response.data;
};

export const apiDelete = async (url, config = {}) => {
  const response = await apiClient.delete(url, config);
  return response.data;
};

export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    console.error('API health check failed:', error);
    return null;
  }
};