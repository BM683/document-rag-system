import React, { useState, useEffect } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import { AuthProvider, useAuth } from "./AuthContext";
import Login from "./components/Login";
import Register from "./components/Register";
import ProtectedRoute from "./components/ProtectedRoute";
import { API_BASE_URL } from "./config";
import "./App.css";

function DocumentApp() {
  const { user, logout } = useAuth();
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [dragOver, setDragOver] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);

  useEffect(() => {
    if (user) {
      fetchDocuments();
    }
  }, [user]);

  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents`, {
        withCredentials: true
      });
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
      if (error.response?.status === 401) {
        // Token expired, will be handled by auth context
        return;
      }
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 5000);
  };

  const handleFileUpload = async () => {
    if (!file) {
      showMessage('error', 'Please select a file first.');
      return;
    }
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const uploadRes = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        withCredentials: true
      });

      const blobName = uploadRes.data.blob_name;

      await axios.post(
        `${API_BASE_URL}/api/files/${encodeURIComponent(blobName)}/embed`,
        null,
        { withCredentials: true }
      );

      showMessage('success', 'File uploaded and indexed successfully!');
      setFile(null);
      // Refresh document list
      fetchDocuments();
    } catch (error) {
      if (error.response?.status === 401) {
        showMessage('error', 'Session expired. Please log in again.');
      } else {
        showMessage('error', `Error uploading or embedding file: ${error.response?.data?.detail || error.message}`);
      }
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async () => {
    if (!question.trim()) {
      showMessage('error', 'Please enter a question.');
      return;
    }
    
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/ask`, null, {
        params: {
          question,
          top_k: 5,
        },
        withCredentials: true
      });
      setAnswer(res.data.answer);
    } catch (error) {
      if (error.response?.status === 401) {
        setAnswer("Session expired. Please log in again.");
      } else {
        setAnswer("Error getting answer: " + (error.response?.data?.detail || error.message));
      }
    }
    setLoading(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleDownload = async (blobName, filename) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents/${encodeURIComponent(blobName)}/download`, {
        responseType: 'blob',
        withCredentials: true
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      showMessage('error', `Error downloading file: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDelete = async (blobName, filename, documentId) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }
    
    try {
      const params = {};
      if (documentId && documentId !== 'None' && documentId !== 'null' && documentId !== null) {
        params.document_id = documentId;
      }
      
      console.log('🗑️ Frontend Delete:', { blobName, filename, documentId, params });
      
      await axios.delete(`${API_BASE_URL}/api/documents/${encodeURIComponent(blobName)}`, {
        params,
        withCredentials: true
      });
      
      showMessage('success', `"${filename}" deleted successfully!`);
      // Refresh document list
      fetchDocuments();
    } catch (error) {
      showMessage('error', `Error deleting file: ${error.response?.data?.detail || error.message}`);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="modern-container">
      {/* Header */}
      <header className="modern-header">
        <div className="header-content">
          <div>
            <h1 className="modern-title">
              ✨ Document RAG Assistant
            </h1>
            <p className="modern-subtitle">
              Ask anything from your documents. Get instant answers.
            </p>
          </div>
          <div className="user-info">
            <span className="user-email">{user?.email}</span>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Message Display */}
      {message.text && (
        <div className={`message-display ${message.type}`}>
          {message.type === 'success' ? (
            '✅'
          ) : (
            '❌'
          )}
          {message.text}
        </div>
      )}

      {/* Main Content */}
      <div className="cards-grid">
        {/* Document Library Section */}
        <div className="modern-card">
          <h2 className="card-title">
            📚 Document Library
          </h2>
          
          {/* Upload Area */}
          <div className="upload-section">
            <div 
              className={`file-upload-area ${dragOver ? 'dragover' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-input').click()}
            >
              <div className="upload-icon">📁</div>
              <div className="upload-text">
                {file ? file.name : 'Click to upload or drag and drop'}
              </div>
              <div className="upload-hint">
                Supports PDF, DOCX, and TXT files
              </div>
            </div>
            
            <input
              id="file-input"
              type="file"
              onChange={handleFileChange}
              className="hidden-file-input"
              accept=".pdf,.docx,.txt"
            />

            <button
              className="modern-button"
              onClick={handleFileUpload}
              disabled={uploading || !file}
            >
              {uploading ? (
                <>
                  ⏳ Processing...
                </>
              ) : (
                <>
                  📄 Upload & Index
                </>
              )}
            </button>
          </div>

          {/* Document List */}
          <div className="document-list-section">
            <h3 className="section-title">Your Documents</h3>
            
            {loadingDocs ? (
              <div className="loading-state">
                <div className="spinner"></div>
                <span>Loading documents...</span>
              </div>
            ) : documents.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">📄</div>
                <p>No documents uploaded yet.</p>
                <p>Upload your first document above to get started!</p>
              </div>
            ) : (
              <div className="document-list">
                {documents.map((doc, index) => (
                  <div key={index} className="document-item">
                    <div className="document-info">
                      <div className="document-name">
                        📄 {doc.filename}
                        {doc.is_indexed && <span className="indexed-badge">✓ Indexed</span>}
                      </div>
                      <div className="document-meta">
                        <span className="file-size">{formatFileSize(doc.size)}</span>
                        {doc.upload_date && (
                          <span className="upload-date">
                            {new Date(doc.upload_date).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="document-actions">
                      <button
                        className="action-button download-button"
                        onClick={() => handleDownload(doc.blob_name, doc.filename)}
                        title="Download document"
                      >
                        ⬇️ Download
                      </button>
                      <button
                        className="action-button delete-button"
                        onClick={() => handleDelete(doc.blob_name, doc.filename, doc.document_id)}
                        title="Delete document"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Ask Section */}
        <div className="modern-card">
          <h2 className="card-title">
            💬 Ask Questions
          </h2>
          
          <div className="modern-input-group">
            <label className="modern-label">Your Question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything about your uploaded documents..."
              className="modern-textarea"
              rows="4"
            />
          </div>

          <button
            className="modern-button"
            onClick={handleAsk}
            disabled={loading || !question.trim()}
          >
            {loading ? (
              <>
                🔍 Analyzing...
              </>
            ) : (
              <>
                ❓ Ask Question
              </>
            )}
          </button>
        </div>
      </div>

      {/* Answer Section */}
      {answer && (
        <div className="answer-card">
          <h3 className="answer-title">
            🧠 AI Response
          </h3>
          <div className="answer-text">
            <ReactMarkdown>{answer}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  const [showRegister, setShowRegister] = useState(false);
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <span>Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        {showRegister ? (
          <Register onSwitchToLogin={() => setShowRegister(false)} />
        ) : (
          <Login onSwitchToRegister={() => setShowRegister(true)} />
        )}
      </>
    );
  }

  return (
    <ProtectedRoute>
      <DocumentApp />
    </ProtectedRoute>
  );
}

function AppWithProvider() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

export default AppWithProvider;
