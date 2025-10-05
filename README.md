# Hackyeah Automation Assistant

A modern desktop application that combines FastAPI backend with Electron + React frontend for intelligent file monitoring and email automation.

## Architecture

- **Backend**: FastAPI server handling all core logic (file watching, AI, email management)
- **Frontend**: Electron app with React UI using Tailwind CSS and modern components
- **Communication**: REST API between frontend and backend

## Features

- 📁 **File Monitoring**: Watch multiple directories for file changes with pattern detection
- 📧 **Email Integration**: Support for IMAP, POP3, and Nylas OAuth with auto-discovery
- 🤖 **AI-Powered**: Gemini integration for pattern recognition and automation planning
- ⚙️ **Modern Settings**: Beautiful form-based configuration instead of raw YAML editing
- 📊 **Real-time Dashboard**: Live monitoring of recent actions and automation status
- 🔍 **AI Interaction Viewer**: Track and review all AI prompts and responses

## Quick Start

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The backend will start on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

This will start both the React dev server and Electron app.

### Production Build

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm run build-electron
```

## Configuration

The app uses `config.yaml` for configuration. You can edit it through the modern Settings UI in the app, or manually:

```yaml
nylas:
  api_key: "your_nylas_api_key"
  client_id: "your_nylas_client_id"
  redirect_uri: "https://blank.page/"
  api_uri: "https://api.us.nylas.com"

gemini:
  api_key: "your_gemini_api_key"

watch:
  dirs:
    - "./"
    - "~/Desktop"
    - "~/Downloads"
  recent_ops_capacity: 100
  pattern_interval_seconds: 10

logging:
  enabled: false
```

## API Endpoints

- `GET /config` - Get current configuration
- `PUT /config` - Update configuration
- `GET /accounts` - List email accounts
- `POST /accounts/email` - Add email account (auto-detect)
- `POST /accounts/oauth` - Get OAuth URL
- `POST /accounts/oauth/exchange` - Exchange OAuth code
- `DELETE /accounts/{id}` - Remove account
- `GET /recent-actions` - Get recent file actions
- `GET /ai-interactions` - Get AI interaction history
- `GET /emails` - Get recent emails

## Technology Stack

- **Backend**: FastAPI, Pydantic, Watchdog, Nylas SDK, Google Generative AI
- **Frontend**: Electron, React, Tailwind CSS, Framer Motion, Headless UI
- **Email**: IMAP, POP3, SMTP, Nylas OAuth
- **AI**: Google Gemini 1.5 Flash

## Development

The project is split into two main directories:
- `backend/` - FastAPI server with all core logic
- `frontend/` - Electron + React application

Both can be developed independently, with the frontend communicating with the backend via HTTP API calls.