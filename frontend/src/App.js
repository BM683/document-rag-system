import React, { useState, useEffect } from "react";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";
import "./App.css";

// Use environment variable or fallback to local for development
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://document-rag-system-511830906232.europe-west1.run.app';

function App() {
  const [sessionNamespace, setSessionNamespace] = useState("");
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    let ns = localStorage.getItem("sessionNamespace");
    if (!ns) {
      ns = uuidv4();
      localStorage.setItem("sessionNamespace", ns);
    }
    setSessionNamespace(ns);
  }, []);

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
      });

      const blobName = uploadRes.data.blob_name;

      await axios.post(
        `${API_BASE_URL}/api/files/${encodeURIComponent(blobName)}/embed`,
        null,
        { params: { namespace: sessionNamespace } }
      );

      showMessage('success', 'File uploaded and indexed successfully!');
      setFile(null);
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
        {/* Upload Section */}
        <div className="modern-card">
          <h2 className="card-title">
            📤 Upload Document
          </h2>
          
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
          <div className="answer-text">{answer}</div>
        </div>
      )}
    </div>
  );
}

export default App;