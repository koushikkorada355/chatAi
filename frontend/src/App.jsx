import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useSelector } from 'react-redux';
import LoginPage from './pages/LoginPage/LoginPage';
import ChatPage from './pages/ChatPage/ChatPage';
import ProtectedRoute from './routes/ProtectedRoute';
import { setAuthToken } from './services/api';

function App() {
  const token = useSelector((state) => state.auth.token);

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/chat" replace />} />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}

export default App;
