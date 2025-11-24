import React, { useEffect } from 'react';
import { useAuth } from '../AuthContext';

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading, getCurrentUser } = useAuth();

  useEffect(() => {
    if (!isAuthenticated && !loading) {
      getCurrentUser();
    }
  }, [isAuthenticated, loading, getCurrentUser]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <span>Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will be handled by App.js to show login
  }

  return children;
}

export default ProtectedRoute;

