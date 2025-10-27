/**
 * Main App Component
 * Root component with routing and context providers
 */

import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { Navbar, ProtectedRoute } from './components';
import {
  Login,
  Register,
  Dashboard,
  ChaptersList,
  ChapterCreate,
  ChapterDetail,
  PDFsList,
  PDFUpload,
  TasksList,
  Search,
} from './pages';

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />

            {/* Chapter Routes */}
            <Route
              path="/chapters"
              element={
                <ProtectedRoute>
                  <ChaptersList />
                </ProtectedRoute>
              }
            />
            <Route
              path="/chapters/create"
              element={
                <ProtectedRoute>
                  <ChapterCreate />
                </ProtectedRoute>
              }
            />
            <Route
              path="/chapters/:id"
              element={
                <ProtectedRoute>
                  <ChapterDetail />
                </ProtectedRoute>
              }
            />

            {/* PDF Routes */}
            <Route
              path="/pdfs"
              element={
                <ProtectedRoute>
                  <PDFsList />
                </ProtectedRoute>
              }
            />
            <Route
              path="/pdfs/upload"
              element={
                <ProtectedRoute>
                  <PDFUpload />
                </ProtectedRoute>
              }
            />

            {/* Task Routes */}
            <Route
              path="/tasks"
              element={
                <ProtectedRoute>
                  <TasksList />
                </ProtectedRoute>
              }
            />

            {/* Search Route */}
            <Route
              path="/search"
              element={
                <ProtectedRoute>
                  <Search />
                </ProtectedRoute>
              }
            />

            {/* Redirect root to dashboard or login */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* 404 Route */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;
