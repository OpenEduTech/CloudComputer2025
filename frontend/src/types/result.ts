import type { QuizSubmission } from './quiz';

// Result types
export interface GradingResult {
  question_id: string;
  is_correct: boolean;
  score: number;
  feedback: string;
  error_type?: string; // "concept", "logic", "expression"
  analysis: string;
}

export interface QuizResult {
  id: string;
  quiz_id: string;
  user_id: string;
  submission: QuizSubmission;
  results: GradingResult[];
  overall_analysis: string;
  score?: number;
  created_at?: string;
}
