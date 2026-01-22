import apiClient from './client';
import type { Quiz, Answer } from '../types/quiz';
import type { QuizResult } from '../types/result';

/**
 * Get a quiz by ID
 * @param quizId - Quiz ID
 * @returns Promise with quiz data
 */
export const getQuiz = async (quizId: string): Promise<Quiz> => {
  try {
    const response = await apiClient.get<Quiz>(`/api/v1/quizzes/${quizId}`);
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Failed to fetch quiz. Please try again.');
  }
};

/**
 * Generate a quiz from content
 * @param content - Parsed PDF content
 * @param title - Quiz title
 * @param count - Number of questions to generate
 * @returns Promise with generated quiz data
 */
export const generateQuiz = async (
  content: string,
  title: string,
  count: number
): Promise<Quiz> => {
  try {
    const response = await apiClient.post<Quiz>('/api/v1/quizzes/generate', null, {
      params: {
        content,
        title,
        count,
      },
    });
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Quiz generation failed. Please try again.');
  }
};

/**
 * Submit quiz answers for grading
 * @param quizId - Quiz ID
 * @param answers - Array of user answers
 * @returns Promise with quiz result data
 */
export const submitQuiz = async (quizId: string, answers: Answer[]): Promise<QuizResult> => {
  try {
    console.log('🔄 submitQuiz: 发送请求到 /submit');
    const response = await apiClient.post<QuizResult>(`/api/v1/quizzes/${quizId}/submit`, {
      quiz_id: quizId,
      answers,
    });
    
    console.log('📥 submitQuiz: 收到响应');
    console.log('📊 response:', response);
    console.log('📊 response.data:', response.data);
    console.log('📊 response.data.id:', response.data?.id);
    console.log('📊 response.data 全部字段:', Object.keys(response.data || {}));
    
    return response.data;
  } catch (error: any) {
    console.error('❌ submitQuiz: 请求失败', error);
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Quiz submission failed. Please try again.');
  }
};

/**
 * Get quiz history for the current user
 * @returns Promise with array of quiz results
 */
export const getQuizHistory = async (): Promise<QuizResult[]> => {
  try {
    const response = await apiClient.get<QuizResult[]>('/api/v1/quizzes/history');
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Failed to fetch quiz history. Please try again.');
  }
};

/**
 * Get a specific quiz result by ID
 * @param resultId - Result ID
 * @returns Promise with quiz result data
 */
export const getQuizResult = async (resultId: string): Promise<QuizResult> => {
  try {
    const response = await apiClient.get<QuizResult>(`/api/v1/quizzes/results/${resultId}`);
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Failed to fetch quiz result. Please try again.');
  }
};
