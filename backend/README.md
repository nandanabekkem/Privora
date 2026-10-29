# Privora Backend

## Architecture and safety

The FastAPI API uses Firestore through Firebase Admin SDK. PostgreSQL, SQLAlchemy models, Alembic migrations, and related scripts remain as a legacy database path; active API routers do not use that database. `DATABASE_URL` is optional for the Firestore API and required for legacy SQLAlchemy/Alembic operations.

User-specific API calls require a Firebase Authentication ID token in `Authorization: Bearer <token>`. The backend verifies the token and authorizes the path user against its UID. New users are provisioned on their first `/auth/me` request. Existing numeric user records must be explicitly linked by an administrator using a `firebase_uid` field; never link based only on an email supplied by a client.

The current Firebase Admin initialization requires a private service-account JSON file at `FIREBASE_CREDENTIALS_PATH`. Application-default credentials/workload identity are not implemented. Do not expose the backend or use real data until Firebase service-account access, Firestore IAM, authentication, and deployment CORS have been configured and reviewed.

Gmail candidates discovered from authorized message headers are saved per user in Firestore with status `UNKNOWN`. Message receipt time is stored as evidence time and is not treated as account activity. Synthetic sample results are returned for demonstration and are not added to the real inventory.

The authenticated analysis endpoint and account-specific chat use local category rules when `NVIDIA_API_KEY` is absent. With the key configured, a user-triggered analysis/chat request sends only service metadata, purpose/catalog text, categories, and sanitized chat text to NVIDIA; raw stored data-record descriptions are excluded. Responses have a 20-second total timeout, a 5-second connect timeout, and validated output shape/size. Provider errors or invalid responses fall back to deterministic local rules and are labelled `rules_fallback` in the API and UI. Configure `NVIDIA_API_KEY` only as a backend secret. AI output is explanatory and does not verify providers or perform actions. The current model is `nvidia/nemotron-3.5-lightning-30b-a3b` at `https://integrate.api.nvidia.com/v1/chat/completions`; live calls require a valid NVIDIA key and were not tested in this workspace.

Deletion requests are drafted as `DELETE_REQUEST_DRAFT` privacy actions and require explicit approval. GitHub and LinkedIn use source-linked official self-service guides; Privora does not submit account closure on those providers' behalf. A service may instead configure `deletion_email` and `deletion_email_source_url` in its Firestore service record. Both the address and evidence URL must be on the service's HTTPS domain. For such catalogued email channels, a separate user-triggered send operation uses the connected user's Gmail account only after approval and a second explicit confirmation in the UI. Gmail must be reauthorized for the `gmail.send` scope. Gmail's confirmed submission is not proof of provider receipt or account deletion. Ambiguous send outcomes are marked `SEND_UNCONFIRMED` and must be checked in Gmail before retrying. On dashboard load, Privora checks at most ten Gmail threads that it sent and records same-service-domain header matches as `REPLY_CANDIDATE`; message content is never read, and the user must confirm the candidate. This provides an in-app status/audit notification only; no push/email notification is configured. Replies to externally sent or self-service requests remain user-reported.

## Firestore and Firebase Authentication setup

Use Python 3.11 or a compatible version supported by the pinned dependencies. From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `FIREBASE_CREDENTIALS_PATH` in `backend/.env` to a private service-account JSON file. Relative paths resolve from `backend/`; the default is `backend/firebase-credentials.json`. Enable Firestore and Firebase Authentication in the same Firebase project. In Firebase Console, enable **Authentication → Sign-in method → Email/Password**.

Register a Firebase Web App. Copy its public web configuration into the repository-root `.env` using [../.env.example](../.env.example), then add the frontend host under **Authentication → Settings → Authorized domains**. Web app config values are client configuration; never expose the Admin service-account file to the browser.

Start the API from `backend/`:

```powershell
python -m uvicorn app.main:app --reload
```

The API is at `http://127.0.0.1:8000`; Swagger UI is at `/docs`. The equivalent entrypoints are `python -m uvicorn main:app` from `backend/` and `python -m uvicorn backend.main:app` from the repository root.

## Gmail discovery

The synthetic endpoint `POST /discovery/run?source=synthetic` returns fabricated sample data. The UI labels it accordingly. For Gmail, a signed-in user starts consent with `POST /discovery/gmail/authorize`; Google returns to `GET /discovery/gmail/callback`; then `POST /discovery/run?source=gmail` scans that user's messages. `GET /discovery/gmail/status` reports whether that user's stored authorization is ready, missing, expired/revoked, or temporarily unavailable. The callback uses one-time state and PKCE. Per-user OAuth credentials are encrypted with Fernet before storage in Firestore. The Gmail provider reads a bounded number of message headers (sender, subject, date); it does not fetch message bodies. Results are candidate accounts, not provider verification.

Google Cloud setup:

1. Enable the Gmail API in the chosen Google Cloud project.
2. Configure the Google Auth Platform consent screen and add intended test users while the app is in testing.
3. Create an OAuth client ID of type **Web application**. Add the deployed frontend origin as an authorized JavaScript origin.
4. Add the exact backend callback URI ending in `/discovery/gmail/callback` as an authorized redirect URI. Set the identical value in `PRIVORA_GMAIL_REDIRECT_URI`.
5. For local development, copy `backend/.env.example` to `backend/.env` and set `PRIVORA_GMAIL_CLIENT_ID`, `PRIVORA_GMAIL_CLIENT_SECRET`, `PRIVORA_GMAIL_REDIRECT_URI`, `PRIVORA_FRONTEND_URL`, and a private `PRIVORA_GMAIL_TOKEN_ENCRYPTION_KEY`. These values are loaded from the backend `.env` file even when Uvicorn is started from the repository root; deployment environment variables take precedence. Generate a Fernet key with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
6. Sign in to Privora and select **Connect Gmail** to grant access for that Google account.

Privora requests `https://www.googleapis.com/auth/gmail.metadata` for bounded header-only discovery and `https://www.googleapis.com/auth/gmail.send` only for explicitly approved email requests. The former is a restricted scope and the latter is sensitive. Existing Gmail connections must reconnect to grant the added send scope. Google states that restricted-scope use by public apps requires OAuth verification, and server-side storage/transmission of restricted-scope data can require a security assessment. See [Google's OAuth Web Server flow](https://developers.google.com/identity/protocols/oauth2/web-server) and [Gmail API scope requirements](https://developers.google.com/workspace/gmail/api/auth/scopes). No Google OAuth client or live Gmail grant is configured here.

Purpose descriptions and self-service guides are curated for the existing GitHub and LinkedIn catalog entries, with official source URLs returned to the UI. These are references to official documentation, not live website checks. For other services, Privora uses stored catalog metadata or reports the purpose/channel as unknown. Email sending is unavailable unless an administrator adds a source-verified `deletion_email` and `deletion_email_source_url` to that service's Firestore record; the bundled service examples do not define email recipients.

## Configuration

See `backend/.env.example` for backend variables:

- `FIREBASE_CREDENTIALS_PATH`: private Firebase Admin service-account file path.
- `PRIVORA_CORS_ORIGINS`: comma-separated list of exact frontend origins.
- `DATABASE_URL`: optional legacy PostgreSQL URL.
- `PRIVORA_MAX_EMAILS`, `PRIVORA_MAX_EMAIL_BODY_LENGTH`: discovery limits.
- `PRIVORA_GMAIL_CLIENT_ID`, `PRIVORA_GMAIL_CLIENT_SECRET`: OAuth Web client values.
- `PRIVORA_GMAIL_REDIRECT_URI`, `PRIVORA_FRONTEND_URL`: exact callback and post-consent frontend origin.
- `PRIVORA_GMAIL_TOKEN_ENCRYPTION_KEY`: Fernet key for encrypted per-user credentials.
- `NVIDIA_API_KEY`: optional server-only key for the existing Nemotron-assisted analysis/chat flow.

See repository-root `.env.example` for `VITE_API_BASE_URL` and Firebase Web App configuration.

## Legacy PostgreSQL setup

To use the retained SQLAlchemy/Alembic path, create a PostgreSQL database and set `DATABASE_URL` in `backend/.env`, for example:

```text
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD_HERE@localhost:5432/privora
```

Replace the placeholder locally and never commit the real password. From `backend/`, run `python -m alembic upgrade head`. Current API routers use Firestore and do not read this PostgreSQL database. Do not delete or migrate existing database files/records as part of this setup.

## Tests

From `backend/`, run `python -m pytest -q`. Tests cover token rejection, cross-user authorization, API behavior, model registration, rules, privacy actions, and synthetic discovery. Gmail OAuth is unit-tested with mock data; no live Firebase or Gmail account was tested.

In this Windows sandbox, TestClient hangs because asyncio's Proactor loop cannot complete local socket-pair setup under sandbox network restrictions. A socket-pair probe works outside the sandbox, and the full suite passed in an isolated Python 3.12 virtual environment outside those restrictions. Run TestClient tests in an environment that permits local loopback sockets; a hung run is not a pass.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/auth/me` | Verify identity and return/create the Privora user profile |
| GET | `/services/` | List services (authentication required) |
| GET | `/data-map/{user_id}` | Retrieve an authorized user's data map |
| GET | `/dormant/{user_id}?days=90` | Find potentially dormant records |
| GET/POST | `/policies/{user_id}` | List or create privacy policies |
| GET | `/rules/{user_id}?days=90` | Generate recorded-data recommendations |
| GET/POST | `/privacy-actions/{user_id}` | List or create proposed actions |
| POST | `/privacy-actions/{user_id}/{action_id}/review` | Review an authorized user's proposal |
| POST | `/privacy-actions/{user_id}/accounts/{account_id}/deletion-draft` | Save an account-specific deletion request draft requiring approval |
| POST | `/privacy-actions/{user_id}/{action_id}/send` | Send an approved draft through Gmail only to a source-verified service email |
| POST | `/privacy-actions/{user_id}/{action_id}/tracking` | Record user-reported sent/reply status after approval |
| POST | `/privacy-actions/{user_id}/check-replies` | Check up to ten Privora-sent Gmail threads for metadata-only reply candidates |
| POST | `/analysis/{user_id}/accounts/{account_id}` | Analyze recorded categories and catalog purpose |
| GET/POST | `/assistant/{user_id}/accounts/{account_id}/messages` | Read or persist an account-specific conversation |
| GET | `/audit-logs/{user_id}` | Retrieve authorized user's audit events |
| GET | `/discovery/health` | Discovery health check |
| POST | `/discovery/gmail/authorize` | Start per-user Gmail OAuth consent |
| GET | `/discovery/gmail/status` | Check the signed-in user's Gmail authorization state |
| GET | `/discovery/gmail/callback` | Complete one-time Google OAuth callback |
| POST | `/discovery/run?source=synthetic` | Run explicitly synthetic sample discovery |
| POST | `/discovery/run?source=gmail` | Infer candidates from authorized Gmail headers and persist them in that user's inventory |

Dormancy and recommendations use recorded data, not live provider activity. Approving a privacy action records a decision only; it does not contact providers or delete accounts.

## Deployment scaffold

The backend Cloud Run container is in `backend/Dockerfile`; Firebase Hosting serves the root `dist/` directory using `firebase.json`. Mount the Firebase Admin service-account JSON as a protected Cloud Run secret file and set `FIREBASE_CREDENTIALS_PATH`; this implementation does not use Application Default Credentials. Grant the Cloud Run runtime identity only the required Firestore access. Configure CORS to the exact Firebase Hosting origin, and set the frontend build-time `VITE_API_BASE_URL` to the Cloud Run API origin with the Firebase Web App values in `VITE_FIREBASE_*`.

Register the exact Gmail redirect URI `https://<cloud-run-host>/discovery/gmail/callback` and authorize the frontend origin in the Google OAuth client. Store the Firebase Admin JSON, Gmail client secret, Gmail token-encryption key, and `NVIDIA_API_KEY` only in the hosting secret manager. Deployment credentials, Firebase Web App values, Gmail OAuth configuration, NVIDIA credentials, and a selected Cloud Run project/region are not available in this workspace; no live integration or deployment has been attempted.
