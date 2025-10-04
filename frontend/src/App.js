import React, { useState, useEffect } from "react";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";

// Use environment variable or fallback to local for development
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://document-rag-system-511830906232.europe-west1.run.app';

function App() {
  const [sessionNamespace, setSessionNamespace] = useState("");
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    let ns = localStorage.getItem("sessionNamespace");
    if (!ns) {
      ns = uuidv4();
      localStorage.setItem("sessionNamespace", ns);
    }
    setSessionNamespace(ns);
  }, []);

  const handleFileUpload = async () => {
    if (!file) return alert("Please select a file first.");
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      // Upload returns blob_name now
      const uploadRes = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const blobName = uploadRes.data.blob_name;  // Use blob_name instead of filename

      // Embed using blob_name
      await axios.post(
        `${API_BASE_URL}/api/files/${encodeURIComponent(blobName)}/embed`,
        null,
        { params: { namespace: sessionNamespace } }
      );

      alert("✅ File uploaded and indexed successfully!");
    } catch (error) {
      alert("❌ Error uploading or embedding file: " + error.message);
    } finally {
      setUploading(false);
    }
  };

  // Ask question
  const handleAsk = async () => {
    if (!question) return alert("Please enter a question.");
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

  return (
    <div style={styles.wrapper}>
      <h1 style={styles.heading}>📚 Document RAG Assistant</h1>
      <p style={styles.subText}>
        Session: <strong>{sessionNamespace}</strong>
      </p>

      {/* Upload Section */}
      <div style={styles.card}>
        <h2 style={styles.sectionTitle}>Upload Document</h2>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
          style={styles.fileInput}
        />
        <button
          style={styles.button}
          onClick={handleFileUpload}
          disabled={uploading}
        >
          {uploading ? "⏳ Uploading..." : "📤 Upload"}
        </button>
      </div>

      {/* Ask Section */}
      <div style={styles.card}>
        <h2 style={styles.sectionTitle}>Ask a Question</h2>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Enter your question about the uploaded documents..."
          style={styles.textArea}
        />
        <button
          style={styles.button}
          onClick={handleAsk}
          disabled={loading}
        >
          {loading ? "🔍 Searching..." : "❓ Ask"}
        </button>
      </div>

      {/* Answer Section */}
      {answer && (
        <div style={styles.answerCard}>
          <h3>💬 Answer:</h3>
          <p style={styles.answerText}>{answer}</p>
        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    maxWidth: "700px",
    margin: "0 auto",
    fontFamily: "Arial, sans-serif",
    padding: "20px",
    color: "#333",
  },
  heading: {
    textAlign: "center",
    fontSize: "2rem",
    marginBottom: "5px",
  },
  subText: {
    textAlign: "center",
    fontSize: "0.9rem",
    color: "#777",
    marginBottom: "20px",
  },
  card: {
    background: "#fff",
    padding: "20px",
    marginBottom: "20px",
    borderRadius: "10px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
  },
  sectionTitle: {
    marginTop: 0,
    fontSize: "1.2rem",
  },
  fileInput: {
    display: "block",
    marginBottom: "10px",
  },
  textArea: {
    width: "100%",
    minHeight: "80px",
    marginBottom: "10px",
    padding: "10px",
    fontSize: "1rem",
    borderRadius: "5px",
    border: "1px solid #ddd",
  },
  button: {
    background: "#007BFF",
    color: "#fff",
    padding: "10px 20px",
    fontSize: "1rem",
    border: "none",
    borderRadius: "5px",
    cursor: "pointer",
  },
  answerCard: {
    background: "#f9f9f9",
    padding: "15px",
    borderRadius: "10px",
    border: "1px solid #ddd",
  },
  answerText: {
    whiteSpace: "pre-wrap",
    margin: 0,
  },
};

export default App;
