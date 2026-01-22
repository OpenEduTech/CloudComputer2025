import apiClient from './client';
import type { RegisterData, TokenResponse, User } from '../types/user';

/**
 * Register a new user
 * @param data - User registration data
 * @returns Promise with user data
 */
export const register = async (data: RegisterData): Promise<User> => {
  try {
    const response = await apiClient.post<User>('/api/v1/auth/register', data);
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Registration failed. Please try again.');
  }
};

/**
 * Login user and get access token
 * @param username - Username or email
 * @param password - User password
 * @returns Promise with token response
 */
export const login = async (username: string, password: string): Promise<TokenResponse> => {
  try {
    // FastAPI OAuth2 expects form data with username and password fields
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await apiClient.post<TokenResponse>('/api/v1/auth/login/access-token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Login failed. Please check your credentials.');
  }
};

/**
 * Get current user info
 * @returns Promise with user data
 */
export const getCurrentUser = async (): Promise<User> => {
  try {
    const response = await apiClient.get<User>('/api/v1/auth/me');
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Failed to get user info.');
  }
};

/**
 * Update current user's grade
 * @param grade - New grade value
 * @returns Promise with updated user data
 */
export const updateUserGrade = async (grade: string): Promise<User> => {
  try {
    const response = await apiClient.put<User>('/api/v1/auth/me', { grade });
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Failed to update grade.');
  }
};
