# Hackyeah Automation Backend

FastAPI backend for the Hackyeah automation application.

## Structure

```
backend/
├── main.py              # Entry point for FastAPI server
├── requirements.txt     # Python dependencies
├── src/                 # Source code
│   ├── main.py         # FastAPI application
│   ├── config.py       # Configuration management
│   ├── agents.py       # AI agents (Pattern, Automation, Python)
│   ├── emails.py       # Email handling (IMAP, POP3, Nylas)
│   ├── gemini_client.py # Google Gemini AI client
│   ├── nylas_handler.py # Nylas email API handler
│   └── recent_ops.py   # File system monitoring
└── README.md           # This file
```

## Running the Backend

```bash
cd backend
python main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### Core
- `GET /` - Root endpoint
- `GET /health` - Health check with service status

### Configuration
- `GET /config` - Get current configuration
- `PUT /config` - Update configuration

### Email Accounts
- `GET /accounts` - List all email accounts
- `POST /accounts/oauth` - Get OAuth URL for Nylas
- `POST /accounts/oauth/exchange` - Exchange OAuth code for access
- `POST /accounts/email` - Add email account (auto-detect servers)
- `DELETE /accounts/{account_id}` - Remove email account

### Email Operations
- `GET /emails` - Get recent emails from all accounts
- `POST /emails/send` - Send email through configured account

### AI & Automation
- `GET /ai-interactions` - Get AI interaction history
- `GET /patterns` - Get detected patterns
- `POST /patterns/execute` - Execute pattern-based automation
- `POST /python/execute` - Execute Python automation script

### File Monitoring
- `GET /recent-actions` - Get recent file system operations

## Configuration

The backend reads configuration from `../config.yaml` (relative to backend directory).

Required configuration:
- `gemini.api_key` - Google Gemini API key
- `nylas.api_key` - Nylas API key (optional)
- `nylas.client_id` - Nylas OAuth client ID (optional)
- `nylas.redirect_uri` - Nylas OAuth redirect URI (optional)

## Dependencies

See `requirements.txt` for Python dependencies.

## Development

The backend is designed to work with the Electron frontend. All API endpoints return JSON responses suitable for web consumption.
