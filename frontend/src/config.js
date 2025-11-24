// config.js - Centralized API configuration
// Vercel automatically injects REACT_APP_* environment variables during build
// Set REACT_APP_API_URL in Vercel dashboard: Settings → Environment Variables

export const API_BASE_URL = 
  process.env.REACT_APP_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? 'https://document-rag-system-511830906232.europe-west1.run.app'
    : 'http://localhost:8000');

// Log configuration (helpful for debugging)
if (process.env.NODE_ENV === 'development') {
  console.log('🔧 Frontend Configuration:');
  console.log(`   API URL: ${API_BASE_URL}`);
  console.log(`   REACT_APP_API_URL: ${process.env.REACT_APP_API_URL || 'not set (using fallback)'}`);
  console.log(`   NODE_ENV: ${process.env.NODE_ENV}`);
}

