import apiClient from './client';
import type { MistakeAnalysis } from '../types/analysis';

/**
 * Get mistake analysis for the current user
 * @returns Promise with mistake analysis data
 */
export const getMistakeAnalysis = async (): Promise<MistakeAnalysis> => {
  try {
    const response = await apiClient.get<MistakeAnalysis>('/api/v1/analysis/mistakes');
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Failed to fetch mistake analysis. Please try again.');
  }
};
