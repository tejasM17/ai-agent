# Deployment to Render

This project is configured for easy deployment to [Render](https://render.com/).

## 1. Prerequisites
- A Render account.
- A Google API Key (for Gemini).

## 2. Deployment Steps

### Option A: Using `render.yaml` (Recommended)
1. Push your code to a GitHub or GitLab repository.
2. Log in to Render.
3. Click **Blueprints** in the top navigation.
4. Connect your repository.
5. Render will automatically detect `render.yaml` and configure the service.
6. **Important:** Go to the service dashboard -> **Environment** and add your `GOOGLE_API_KEY`.

### Option B: Manual Web Service Setup
1. Create a new **Web Service** on Render.
2. Connect your repository.
3. Use the following settings:
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
4. Add **Environment Variables**:
   - `GOOGLE_API_KEY`: Your secret key.
   - `PORT`: `10000` (or leave default, Render usually handles this).

## 3. Local Development
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in your `GOOGLE_API_KEY`.
3. Run the app:
   ```bash
   python main.py
   ```

## 4. Key Files Added
- `requirements.txt`: Updated with `gunicorn`.
- `render.yaml`: Infrastructure-as-code configuration for Render.
- `Procfile`: Command specification for Render/Heroku.
- `.env.example`: Template for environment variables.
- `main.py`: Updated to respect the `PORT` environment variable.
