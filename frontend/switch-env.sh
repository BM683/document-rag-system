#!/bin/bash

# Environment switcher script for Document RAG System

case "$1" in
  "local")
    echo "🔧 Switching to LOCAL backend..."
    echo "REACT_APP_API_URL=http://localhost:8000" > .env.local
    echo "✅ Frontend will now use: http://localhost:8000"
    echo "💡 Make sure your backend is running on port 8000"
    ;;
  "production")
    echo "🔧 Switching to PRODUCTION backend..."
    echo "REACT_APP_API_URL=https://document-rag-system-511830906232.europe-west1.run.app" > .env.local
    echo "✅ Frontend will now use: https://document-rag-system-511830906232.europe-west1.run.app"
    ;;
  "status")
    echo "📊 Current environment configuration:"
    if [ -f .env.local ]; then
      echo "   .env.local: $(cat .env.local)"
    else
      echo "   .env.local: Not found"
    fi
    if [ -f .env ]; then
      echo "   .env: $(cat .env)"
    else
      echo "   .env: Not found"
    fi
    ;;
  *)
    echo "Usage: $0 {local|production|status}"
    echo ""
    echo "Commands:"
    echo "  local      - Switch to local backend (localhost:8000)"
    echo "  production - Switch to production backend (Cloud Run)"
    echo "  status     - Show current environment configuration"
    echo ""
    echo "Examples:"
    echo "  $0 local      # Use local backend"
    echo "  $0 production # Use deployed backend"
    echo "  $0 status     # Check current config"
    ;;
esac
