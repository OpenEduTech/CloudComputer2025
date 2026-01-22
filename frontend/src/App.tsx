import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AppLayout } from './components/AppLayout';
import { Spin } from 'antd';
import './App.css';

// Lazy load page components for code splitting
const Home = lazy(() => import('./pages/Home').then(module => ({ default: module.Home })));
const Login = lazy(() => import('./pages/Login').then(module => ({ default: module.Login })));
const Register = lazy(() => import('./pages/Register').then(module => ({ default: module.Register })));
const Quiz = lazy(() => import('./pages/Quiz').then(module => ({ default: module.Quiz })));
const Results = lazy(() => import('./pages/Results').then(module => ({ default: module.Results })));
const MistakeBook = lazy(() => import('./pages/MistakeBook').then(module => ({ default: module.MistakeBook })));
const Profile = lazy(() => import('./pages/Profile').then(module => ({ default: module.Profile })));

// Loading fallback component
const PageLoader = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    minHeight: '100vh' 
  }}>
    <Spin size="large" />
  </div>
);

/**
 * App component
 * Root component with routing configuration and code splitting
 * 
 * Routes:
 * - Public routes: /login, /register
 * - Protected routes: /, /quiz/:quizId, /results/:resultId, /mistakes
 * - Catch-all route redirects to /
 * 
 * Performance optimizations:
 * - Lazy loading of route components
 * - Code splitting for better initial load time
 */
function App() {
  return (
    <BrowserRouter>
      <div className="fade-in">
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected Routes - wrapped with ProtectedRoute and AppLayout */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<Home />} />
              <Route path="/quiz/:quizId" element={<Quiz />} />
              <Route path="/results/:resultId" element={<Results />} />
              <Route path="/mistakes" element={<MistakeBook />} />
              <Route path="/profile" element={<Profile />} />
            </Route>

            {/* Catch-all route - redirect to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </div>
    </BrowserRouter>
  );
}

export default App;
