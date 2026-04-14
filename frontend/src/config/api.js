// // src/config/api.js
/**
 * Axios API client configuration
 * Handles requests, interceptors, and error handling
 */

import axios from 'axios';

// ═══════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════

const API_BASE_URL =
  typeof window !== 'undefined' && window.API_BASE_URL
    ? window.API_BASE_URL
    : 'http://localhost:8000/api';

const API_TIMEOUT = 30000;
const DEBUG = true;  // Set to false in production

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
    'Accept': 'application/json',
  },
});

// ═══════════════════════════════════════════════════════════════
// REQUEST INTERCEPTOR
// ═══════════════════════════════════════════════════════════════

apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Debug logging
    if (DEBUG) {
      console.log(`📡 API Request: ${config.method.toUpperCase()} ${config.url}`);
    }

    return config;
  },
  (error) => {
    if (DEBUG) {
      console.error('❌ Request error:', error);
    }
    return Promise.reject(error);
  }
);

// ═════���═════════════════════════════════════════════════════════
// RESPONSE INTERCEPTOR
// ═══════════════════════════════════════════════════════════════

apiClient.interceptors.response.use(
  (response) => {
    // Debug logging
    if (DEBUG) {
      console.log(`✅ API Response: ${response.status} ${response.statusText}`);
    }

    return response;
  },
  (error) => {
    // Handle errors
    const status = error.response?.status;
    const detail = error.response?.data?.detail || error.message;

    if (DEBUG) {
      console.error(`❌ API Error: ${status} - ${detail}`);
    }

    // Handle 401 Unauthorized
    if (status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }

    // Handle 403 Forbidden
    if (status === 403) {
      console.error('Access denied. Insufficient permissions.');
    }

    // Handle 500 Server Error
    if (status === 500) {
      console.error('Server error. Please try again later.');
    }

    return Promise.reject(error);
  }
);

// ═══════════════════════════════════════════════════════════════
// EXPORT
// ═══════════════════════════════════════════════════════════════

export default apiClient;

// ═══════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════

/**
 * Make GET request
 */
export const apiGet = async (url, config = {}) => {
  const response = await apiClient.get(url, config);
  return response.data;
};

/**
 * Make POST request
 */
export const apiPost = async (url, data = {}, config = {}) => {
  const response = await apiClient.post(url, data, config);
  return response.data;
};

/**
 * Make PATCH request
 */
export const apiPatch = async (url, data = {}, config = {}) => {
  const response = await apiClient.patch(url, data, config);
  return response.data;
};

/**
 * Make DELETE request
 */
export const apiDelete = async (url, config = {}) => {
  const response = await apiClient.delete(url, config);
  return response.data;
};

/**
 * Check API health
 */
export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    console.error('API health check failed:', error);
    return null;
  }
};



// import axios from "axios";

// const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
// const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT || 30000);

// const apiClient = axios.create({
//   baseURL: API_BASE_URL,
//   timeout: API_TIMEOUT,
//   headers: { "Content-Type": "application/json" },
// });

// export default apiClient;