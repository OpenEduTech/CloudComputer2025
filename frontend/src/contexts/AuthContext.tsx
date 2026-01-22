import React, { createContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { User, RegisterData, TokenResponse } from '../types/user';
import * as authApi from '../api/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

const TOKEN_KEY = 'access_token';
const USER_KEY = 'user_data';

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const isAuthenticated = !!token && !!user;

  /**
   * Check authentication status on app initialization
   * Validates stored token and user data
   */
  const checkAuth = async (): Promise<void> => {
    setIsLoading(true);
    try {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      const storedUser = localStorage.getItem(USER_KEY);

      if (storedToken && storedUser) {
        // Parse stored user data
        const userData = JSON.parse(storedUser) as User;
        setToken(storedToken);
        setUser(userData);
      }
    } catch (error) {
      // If there's an error parsing stored data, clear it
      console.error('Error checking auth:', error);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Login user with credentials
   * @param username - Username or email
   * @param password - User password
   */
  const login = async (username: string, password: string): Promise<void> => {
    try {
      const tokenResponse: TokenResponse = await authApi.login(username, password);
      
      // Store token in localStorage
      localStorage.setItem(TOKEN_KEY, tokenResponse.access_token);
      setToken(tokenResponse.access_token);

      // Create user object from username (backend doesn't return full user on login)
      // In a real app, you might want to fetch user details after login
      const userData: User = {
        id: '', // Will be populated by backend or subsequent API call
        username: username,
        email: '', // Will be populated by backend or subsequent API call
      };
      
      localStorage.setItem(USER_KEY, JSON.stringify(userData));
      setUser(userData);
    } catch (error) {
      // Clear any partial state on error
      setToken(null);
      setUser(null);
      throw error;
    }
  };

  /**
   * Register a new user
   * @param userData - User registration data
   */
  const register = async (userData: RegisterData): Promise<void> => {
    try {
      await authApi.register(userData);
      // Note: Registration doesn't automatically log in the user
      // User needs to login after successful registration
    } catch (error) {
      throw error;
    }
  };

  /**
   * Logout user and clear stored data
   */
  const logout = (): void => {
    // Clear token and user from state
    setToken(null);
    setUser(null);
    
    // Clear token and user from localStorage
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };

  // Check authentication on component mount
  useEffect(() => {
    checkAuth();
  }, []);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
