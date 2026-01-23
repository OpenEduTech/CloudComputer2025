// Quiz types
export interface Question {
  id: string;
  type: 'multiple_choice' | 'short_answer';
  content: string;  // 题目内容
  options?: string[]; // For multiple choice
  correct_answer: string;
  explanation?: string;
  difficulty: string;  // "easy", "medium", "hard"
  knowledge_point: string;
}

export interface Quiz {
  id: string;
  _id?: string;  // MongoDB ID (别名)
  title: string;
  user_id: string;
  questions: Question[];
  created_at?: string;
}

export interface Answer {
  question_id: string;
  user_answer: string; // For multiple choice: option text; For short answer: image URL
}

export interface QuizSubmission {
  quiz_id: string;
  answers: Answer[];
}
