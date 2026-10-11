# Privora — Backend

## 1. Project Overview

Privora is a Personal Data Lifecycle Agent that helps users understand and manage the personal information they may have shared with online services.

The backend provides REST APIs for managing services, accounts, personal data records, privacy policies, dormant-account detection, privacy recommendations, and user-reviewed privacy actions.

**Technology Stack**
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic

## 2. Backend Features

- **Personal Data Map:** Retrieves mapped accounts, services, and personal data records.
- **Dormant Account Detection:** Identifies accounts that have had no recorded activity for a configured period.
- **Rules Engine:** Generates recommendations based on recorded account activity and supported policy settings.
- **Privacy Policies:** Creates and retrieves user privacy policies.
- **Privacy Action Management:** Creates, lists, and reviews proposed privacy actions.
- **Audit Information:** Records privacy action status and review timestamps.
- **Database Migrations:** Uses Alembic to manage database schema changes.
- **API Documentation:** Provides interactive Swagger documentation through FastAPI.

## 3. Project Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── data_map.py
│   │   ├── dormant.py
│   │   ├── policies.py
│   │   ├── privacy_actions.py
│   │   ├── rules.py
│   │   └── services.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── base.py
│   ├── services/
│   │   └── rules_engine.py
│   └── main.py
├── alembic/
│   └── versions/
├── tests/
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
├── seed_services.py
└── README.md
```

## 4. Prerequisites

Install the following before running the backend:

- Python 3.11 or a compatible version supported by the installed dependencies
- PostgreSQL
- Git

## 5. Installation and Setup

### Step 1: Open the backend directory

```powershell
cd backend
```

### Step 2: Create a virtual environment

```powershell
python -m venv .venv
```

### Step 3: Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### Step 5: Configure environment variables

Copy `.env.example` to `.env` in the backend directory.

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace the placeholder with your own PostgreSQL connection URL.

Example format:

```text
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD_HERE@localhost:5432/privora
```

Replace `YOUR_PASSWORD_HERE` with your local PostgreSQL password. Make sure the `privora` database already exists.

**Security:** Never commit `.env` or share your actual database password. Use `.env.example` with placeholder values for configuration documentation.

### Step 6: Apply database migrations

From the backend directory, run:

```powershell
python -m alembic upgrade head
```

This creates or updates the database tables defined by the migration history.

### Step 7: Start the API server

```powershell
python -m uvicorn app.main:app --reload
```

The backend should be available at:

`http://127.0.0.1:8000`

Keep the terminal running while testing the API.

## 6. API Documentation

Open the following URL in your browser:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Swagger UI allows developers to inspect endpoints, provide request parameters, submit requests, and review responses.

## 7. Available API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check backend health |
| GET | `/services/` | Retrieve available services |
| GET | `/data-map/{user_id}` | Retrieve a user's Personal Data Map |
| GET | `/dormant/{user_id}?days=90` | Identify potentially dormant accounts |
| GET | `/policies/{user_id}` | Retrieve a user's privacy policies |
| POST | `/policies/{user_id}` | Create a privacy policy |
| GET | `/rules/{user_id}?days=90` | Generate privacy recommendations |
| POST | `/privacy-actions/{user_id}` | Create a proposed privacy action |
| GET | `/privacy-actions/{user_id}` | List a user's privacy actions |
| POST | `/privacy-actions/{user_id}/{action_id}/review` | Approve or reject a proposed action |

The `days` query parameter configures the inactivity threshold for the dormant-account and rules endpoints.

Refer to Swagger UI for request schemas, required fields, and example responses.

## 8. Database Models

The backend defines the following core models:

- **User:** Stores user information.
- **Service:** Represents an online service or platform.
- **Account:** Represents a user's account with a service.
- **DataRecord:** Represents mapped personal data associated with an account.
- **Policy:** Stores a user's privacy policy.
- **PrivacyAction:** Tracks proposed privacy actions and their review status.

SQLAlchemy manages database access, and Alembic manages schema migrations.

## 9. Running Tests

From the backend directory, activate the virtual environment and run:

```powershell
python -m pytest -q
```

The test suite covers API health, model registration, data-map retrieval, dormant-account detection, policies, rules-engine behavior, and privacy-action workflows.

## 10. Development Notes and Limitations

- Dormant-account detection uses activity information recorded in the database. It does not independently discover activity on external platforms.
- The rules engine supports deterministic recommendations and limited inactivity-policy interpretation. It is not a general natural-language policy reasoning system.
- Privacy actions are proposed and reviewed through the API. Approval does not automatically delete accounts, contact services, or execute external privacy requests.
- The current development backend does not provide complete authentication or authorization. It must not be treated as production-ready or exposed publicly with real personal data until appropriate security controls are implemented.
- External account discovery, integrations, and AI-based reasoning depend on their respective project components and are not provided by these endpoints alone.

## 11. Security Guidelines

- Keep database credentials in the local `.env` file.
- Never commit passwords, API keys, access tokens, or other secrets.
- Use `.env.example` to document required environment variables without exposing real credentials.
- Use test data during development.
- Implement and verify authentication, authorization, input validation, and secure handling of personal data before production deployment.

## 12. Project Goal

The goal of the Privora backend is to provide a reliable foundation for mapping personal data, identifying potentially forgotten accounts, applying privacy rules, and managing user-reviewed privacy actions through a REST API.
