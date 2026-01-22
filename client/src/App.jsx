/**
 * PatPat-Inconsistency-Hunter 主应用组件
 * 长文本事实卫士 - React主入口组件
 */

import { useState, useCallback } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import AnalyzePage from './pages/AnalyzePage'
import ResultPage from './pages/ResultPage'
import DashboardPage from './pages/DashboardPage'
import CollaboratePage from './pages/CollaboratePage'
import CollaborateRoomPage from './pages/CollaborateRoomPage'
import JoinRoomPage from './pages/JoinRoomPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ProfilePage from './pages/ProfilePage'

function App() {
  return (
    <AuthProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/analyze" element={<AnalyzePage />} />
            <Route path="/result/:taskId" element={<ResultPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/collaborate" element={<CollaboratePage />} />
            <Route path="/collaborate/:roomId" element={<CollaborateRoomPage />} />
            <Route path="/collaborate/:roomId/join" element={<JoinRoomPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Routes>
        </Layout>
      </Router>
    </AuthProvider>
  )
}

export default App

