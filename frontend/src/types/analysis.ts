import type { Question } from './quiz';
import type { GradingResult } from './result';

// Analysis types
export interface MistakeAnalysis {
  weak_points: Array<{
    knowledge_point: string;
    error_count: number;
    error_types: string[];
  }>;
  recommendations: string[];
  recent_mistakes: Array<{
    question: Question;
    user_answer: string;
    result: GradingResult;
  }>;
}
