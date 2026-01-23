import axios from 'axios';
import { message } from 'antd';

// Create base Axios instance with configuration
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 200000, // 120秒，用于LLM调用
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Add Authorization header from localStorage
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Get user-friendly error message from error object
 * Handles various error scenarios with appropriate messaging
 */
const getErrorMessage = (error: any): string => {
  // Network errors (no response from server)
  if (!error.response) {
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      return 'Request timeout. Please check your connection and try again.';
    }
    if (error.message === 'Network Error') {
      return 'Network error. Please check your internet connection.';
    }
    return 'Unable to connect to the server. Please try again later.';
  }

  // HTTP error responses
  const status = error.response.status;
  const data = error.response.data;

  // Extract error message from response
  if (data?.detail) {
    return typeof data.detail === 'string' ? data.detail : 'An error occurred';
  }
  if (data?.message) {
    return data.message;
  }

  // Default messages based on status code
  switch (status) {
    case 400:
      return 'Invalid request. Please check your input.';
    case 401:
      return 'Session expired. Please log in again.';
    case 403:
      return 'You do not have permission to perform this action.';
    case 404:
      return 'The requested resource was not found.';
    case 409:
      return 'This resource already exists.';
    case 422:
      return 'Validation error. Please check your input.';
    case 500:
      return 'Server error. Please try again later.';
    case 503:
      return 'Service temporarily unavailable. Please try again later.';
    default:
      return `An error occurred (${status}). Please try again.`;
  }
};

// Response interceptor: Handle errors and provide user-friendly messages
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Get user-friendly error message
    const errorMessage = getErrorMessage(error);

    // Handle 401 Unauthorized - session expired
    if (error.response?.status === 401) {
      // Clear token and user data
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_data');
      
      // Show session expired message
      message.error('Session expired. Please log in again.');
      
      // Redirect to login page
      window.location.href = '/login';
    }

    // Attach user-friendly message to error object
    error.message = errorMessage;

    return Promise.reject(error);
  }
);

export default apiClient;
