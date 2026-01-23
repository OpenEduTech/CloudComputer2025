// Material types
export interface Material {
  id: string;
  filename: string;
  user_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  content?: string;
  created_at?: string;
}
