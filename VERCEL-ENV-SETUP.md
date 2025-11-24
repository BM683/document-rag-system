# Setting Up API URL in Vercel

Vercel automatically injects environment variables that start with `REACT_APP_` during the build process. No code changes needed!

## Steps to Set API URL in Vercel

1. **Go to your Vercel project dashboard**
   - Navigate to your project: https://vercel.com/your-username/your-project

2. **Open Settings → Environment Variables**

3. **Add the environment variable:**
   - **Name**: `REACT_APP_API_URL`
   - **Value**: Your backend API URL (e.g., `https://document-rag-system-511830906232.europe-west1.run.app`)
   - **Environment**: Select which environments to apply to:
     - ✅ Production
     - ✅ Preview (optional, for PR previews)
     - ✅ Development (optional, for local dev)

4. **Save and Redeploy**
   - After saving, Vercel will automatically trigger a new build
   - Or manually redeploy from the Deployments tab

## That's It!

The frontend will automatically use the `REACT_APP_API_URL` value from Vercel during the build. No code changes needed - the `config.js` file already reads from `process.env.REACT_APP_API_URL`.

## Verify It's Working

After deployment, check the browser console. You should see logs showing which API URL is being used (in development mode).

## Different URLs for Different Environments

You can set different values for Production, Preview, and Development:
- **Production**: `https://your-production-api.run.app`
- **Preview**: `https://your-preview-api.run.app` (or same as production)
- **Development**: `http://localhost:8000` (for local development)

## Troubleshooting

- **Variable not working?** Make sure it starts with `REACT_APP_` prefix
- **Not updating?** Redeploy after changing environment variables
- **Check build logs** in Vercel to see if the variable is being injected

