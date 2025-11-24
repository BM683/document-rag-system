# API URL Configuration Guide

The frontend needs to know the backend API URL. This is configured via environment variables that are embedded at **build time** (not runtime) in React apps.

## How to Set the API URL

### Option 1: Environment Variable (Recommended)

Set the `REACT_APP_API_URL` environment variable before building:

```bash
# For local development
export REACT_APP_API_URL=http://localhost:8000
npm start

# For production build
export REACT_APP_API_URL=https://your-backend-url.run.app
npm run build
```

### Option 2: .env.local File (For Local Development)

Create a `.env.local` file in the `frontend/` directory:

```bash
# frontend/.env.local
REACT_APP_API_URL=http://localhost:8000
```

Then run:
```bash
npm start
```

### Option 3: Use the Switch Script

The project includes a convenience script:

```bash
# Switch to local backend
./switch-env.sh local

# Switch to production backend
./switch-env.sh production

# Check current configuration
./switch-env.sh status
```

### Option 4: Docker Build (For Production)

When building the Docker image, pass the environment variable:

```bash
docker build --build-arg REACT_APP_API_URL=https://your-backend-url.run.app -t your-image .
```

Or set it in your CI/CD pipeline (Cloud Build, GitHub Actions, etc.)

## For Cloud Run Deployment

The API URL is set in `cloud-run-service.yaml`:

```yaml
env:
- name: REACT_APP_API_URL
  value: "https://your-backend-url.run.app"
```

**Important**: For React apps, environment variables must be set at **build time**, not runtime. If you're using Cloud Build, set it in your `cloudbuild.yaml`:

```yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '--build-arg', 'REACT_APP_API_URL=https://your-backend-url.run.app', '-t', 'gcr.io/$PROJECT_ID/frontend', './frontend']
```

## Current Configuration

- **Default (Development)**: `http://localhost:8000`
- **Default (Production)**: `https://document-rag-system-511830906232.europe-west1.run.app`
- **Config File**: `frontend/src/config.js`

## Troubleshooting

1. **API URL not updating**: Remember that React embeds env vars at build time. You must rebuild after changing the URL.

2. **Check current URL**: Look at browser console logs - the config file logs the API URL being used.

3. **Verify environment variable**: 
   ```bash
   echo $REACT_APP_API_URL
   ```

4. **For production builds**: Always set `REACT_APP_API_URL` explicitly - don't rely on fallbacks.

