import React, { useState, useEffect } from "react";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";
import ReactMarkdown from "react-markdown";
import "./App.css";

// Use environment variable or fallback to local for development
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://document-rag-system-511830906232.europe-west1.run.app';

// Debug: Log which API URL is being used
console.log('🔧 Frontend Configuration:');
console.log(`   API URL: ${API_BASE_URL}`);
console.log(`   Environment: ${process.env.NODE_ENV}`);
console.log(`   REACT_APP_API_URL: ${process.env.REACT_APP_API_URL}`);

function App() {
  const [sessionNamespace, setSessionNamespace] = useState("");
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
    let ns = localStorage.getItem("sessionNamespace");
    if (!ns) {
      ns = uuidv4();
      localStorage.setItem("sessionNamespace", ns);
    }
    setSessionNamespace(ns);
    fetchDocuments(ns);
  }, []);

  const fetchDocuments = async (namespace) => {
    if (!namespace) return;
    
    setLoadingDocs(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents`, {
        params: { namespace }
      });
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
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
        params: { namespace: sessionNamespace }
      });

      const blobName = uploadRes.data.blob_name;

      await axios.post(
        `${API_BASE_URL}/api/files/${encodeURIComponent(blobName)}/embed`,
        null,
        { params: { namespace: sessionNamespace } }
      );

      showMessage('success', 'File uploaded and indexed successfully!');
      setFile(null);
      // Refresh document list
      fetchDocuments(sessionNamespace);
    } catch (error) {
      showMessage('error', `Error uploading or embedding file: ${error.message}`);
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
          namespace: sessionNamespace,
        },
      });
      setAnswer(res.data.answer);
    } catch (error) {
      setAnswer("Error getting answer: " + error.message);
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
        responseType: 'blob'
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
      showMessage('error', `Error downloading file: ${error.message}`);
    }
  };

  const handleDelete = async (blobName, filename, documentId) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }
    
    try {
      const params = { namespace: sessionNamespace };
      if (documentId && documentId !== 'None' && documentId !== 'null' && documentId !== null) {
        params.document_id = documentId;
      }
      
      console.log('🗑️ Frontend Delete:', { blobName, filename, documentId, params });
      
      await axios.delete(`${API_BASE_URL}/api/documents/${encodeURIComponent(blobName)}`, {
        params
      });
      
      showMessage('success', `"${filename}" deleted successfully!`);
      // Refresh document list
      fetchDocuments(sessionNamespace);
    } catch (error) {
      showMessage('error', `Error deleting file: ${error.message}`);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="modern-container">
      {/* Header */}
      <header className="modern-header">
        <h1 className="modern-title">
          ✨ Document RAG Assistant
        </h1>
        <p className="modern-subtitle">
          Ask anything from your documents. Get instant answers.
        </p>
        <div className="session-info">
          🗄️ Session: <strong>{sessionNamespace}</strong>
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

export default App;