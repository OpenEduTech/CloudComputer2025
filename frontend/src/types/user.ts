// User types
export interface User {
  id: string;
  username: string;
  email: string;
  grade?: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  grade: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
