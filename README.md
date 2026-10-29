# Privora

Privora is a personal data lifecycle and digital-footprint management assistant. It helps people discover candidate online services from available evidence, organize an account inventory, review recorded and inferred data categories, and prepare privacy-related actions for their approval.

Gmail evidence and locally stored records can help users investigate their digital footprint, but they do not prove account ownership, current activity, or everything a provider holds. Privora does not independently delete third-party accounts or confirm erasure.

## Contents

- [Current status](#current-status)
- [How Privora works](#how-privora-works)
- [Implemented functionality](#implemented-functionality)
- [Architecture](#architecture)
- [Technology](#technology)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Configuration reference](#configuration-reference)
- [Google OAuth setup](#google-oauth-setup)
- [Using the application](#using-the-application)
- [Privacy and limitations](#privacy-and-limitations)
- [Tests and checks](#tests-and-checks)
- [Contributing](#contributing)
- [License and acknowledgements](#license-and-acknowledgements)

## Current status

- The active FastAPI API uses Firebase Authentication for identity verification and Firestore for application data. PostgreSQL, SQLAlchemy, Alembic migrations, and related scripts remain as a separate legacy database path.
- The frontend has Firebase email/password sign-in and supports Gmail authorization. Gmail discovery reads bounded message metadata and stores service candidates in the signed-in user's inventory.
- Synthetic sample discovery is available for local/demo use and is explicitly labelled as synthetic.
- Privacy analysis and the account-aware assistant currently use local rules and mock/local output. The registered application routes do not call NVIDIA or another AI provider. Historical NVIDIA response labels may appear on older saved chat messages.
- No live Gmail authorization or production deployment is verified by this repository snapshot. Configure external services before expecting those integrations to work.

## How Privora works

1. A user signs in through Firebase Authentication. The backend verifies the Firebase ID token and scopes user data to the authenticated identity.
2. The user may connect Gmail through Google OAuth. Privora scans a bounded number of message headers and uses sender/subject metadata to infer possible service associations; it does not read message bodies for discovery.
3. The application organizes discovered candidates, available account records, and evidence in a Firestore-backed inventory.
4. Local rules provide sensitivity assessments and KEEP/REVIEW recommendations. The account-specific assistant uses stored context and local rules, not a live AI provider.
5. Users may prepare privacy or deletion-request drafts. Eligible email drafts require user approval and a separate explicit send confirmation before Privora attempts submission through Gmail.

## Implemented functionality

- **Discovery:** bounded Gmail metadata scanning and explicitly synthetic sample results. Gmail-derived services are candidates, not confirmed accounts.
- **Inventory and evidence:** account records, activity/evidence dates, and recorded versus Gmail-inferred categories are stored separately where supported. Gmail evidence is not treated as proof of ownership or recent activity.
- **Recommendations:** deterministic local KEEP/REVIEW rules use the available account, activity, recorded data, and saved policy context. Recommendations are informational.
- **Privacy analysis:** local category/description heuristics estimate sensitivity for records stored in Privora. They do not audit a provider's systems.
- **Account-aware assistant:** account-specific local responses and conversation history are persisted in Firestore. This is not AI-provider inference.
- **Privacy policies and actions:** users can manage policy records and review privacy actions. Deletion-request drafts support approval/rejection and audit logging.
- **Request sending and tracking:** supported, source-verified email channels can be submitted only after approval and a second confirmation. A Gmail-confirmed submission is not proof of provider receipt or deletion. Users can record external request/reply status as user-reported. For requests sent by Privora, the app can check a bounded set of Gmail thread headers and surface possible same-domain replies for user confirmation.
- **Service information:** purpose descriptions and request channels use catalogued information and source links where available. Privora does not crawl services or continuously verify their current policies.

## Architecture

```text
src/ (React + Vite)
  ├─ Firebase Authentication in the browser
  └─ authenticated JSON requests to the FastAPI API
                 │
                 ▼
backend/app/ (FastAPI routes, Firebase token verification, Firestore persistence)
  └─ backend/discovery/ (Gmail OAuth, metadata provider, candidate discovery)
                 │
                 ▼
             Firestore
```

The browser obtains a Firebase ID token and sends it as a Bearer token. The backend verifies it with Firebase Admin and authorizes user-specific data against the token UID. Gmail OAuth state is associated with that Firebase UID; Gmail credentials are encrypted before being stored in Firestore. Firebase Admin currently initializes from a service-account JSON file path; application-default credentials/workload identity are not implemented.

Important repository paths:

| Path | Purpose |
| --- | --- |
| `src/` | React application, Firebase Web SDK initialization, API client, and styles |
| `src/App.tsx` | Main application views and user workflows |
| `src/firebase.ts` | Firebase Web App and Authentication initialization |
| `src/api.ts` | Authenticated frontend requests to the backend |
| `backend/app/api/` | FastAPI routes for inventory, analysis, assistant, policies, actions, and audit history |
| `backend/app/core/` | Configuration, authentication, Firebase Admin, and Firestore helpers |
| `backend/app/services/` | Local rules, privacy analysis, and service metadata |
| `backend/discovery/` | Synthetic/Gmail discovery pipeline, Gmail provider, and OAuth storage |
| `backend/tests/`, `backend/discovery/tests/` | Backend and discovery tests |
| `backend/alembic/` | Retained legacy SQLAlchemy migrations |
| `backend/seed_services.py`, `backend/seed_firestore.py` | Service catalog and Firestore seed utilities |
| `backend/Dockerfile` | Backend container build |
| `firebase.json` | Firebase Hosting configuration for the frontend `dist/` output and SPA routes |

## Technology

- **Frontend:** React 19, TypeScript, Vite 8, Tailwind CSS 4, Firebase Web SDK.
- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic Settings.
- **Active persistence and identity:** Google Cloud Firestore through Firebase Admin SDK; Firebase Authentication email/password in the frontend.
- **Gmail:** Gmail API via Google API Python client and Google OAuth authorization-code flow with PKCE.
- **Legacy database support:** SQLAlchemy, PostgreSQL driver, and Alembic remain in the repository; the active API uses Firestore.
- **Tests:** pytest and HTTPX-based FastAPI test tooling; frontend checks use TypeScript and the Vite production build.

The repository includes a separate historical `ai_agent/` Nemotron module, but the current registered analysis and assistant routes do not use it. `NVIDIA_API_KEY` is not needed for those current workflows.

## Prerequisites

- Windows PowerShell (commands below), Git, Node.js 22, and pnpm 10.34.3 as declared in `.mise.toml`.
- Python 3.12 is recommended for local backend development; Python 3.11 or newer is supported by the backend source/dependencies.
- A Firebase project with Authentication and Firestore enabled for authenticated/live use.
- A Google Cloud project, OAuth Web client, Gmail API, and OAuth consent configuration for Gmail authorization. These are optional for local synthetic discovery.
- A PostgreSQL instance only if using the retained legacy SQLAlchemy/Alembic path.

## Local setup

### 1. Clone and install the frontend

```powershell
git clone https://github.com/YOUR-ACCOUNT/Privora.git Privora
Set-Location .\Privora
pnpm install --frozen-lockfile
Copy-Item .env.example .env
```

Replace the example clone URL with the repository URL you have access to.

Fill the local frontend configuration from your Firebase Web App and backend settings. Never commit `.env` files or put backend credentials in frontend variables.

### 2. Create the backend environment

Open another PowerShell terminal:

```powershell
Set-Location .\Privora\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set up a Firebase project, enable Firestore and Firebase Authentication email/password, and keep the Firebase Admin service-account JSON in a private location. Set `FIREBASE_CREDENTIALS_PATH` to that file. Do not put it in the frontend, commit it, or paste its contents into an issue or chat.

### 3. Configure and start the backend

From `backend/`, configure the backend settings described below, then run:

```powershell
python -m uvicorn app.main:app --reload
```

By default, the API is at `http://127.0.0.1:8000`, health check at `/health`, and interactive API documentation at `http://127.0.0.1:8000/docs`.

### 4. Start the frontend

From the repository root in a separate terminal:

```powershell
pnpm dev
```

Vite is configured to use port `8443` by default, so the local app is at `http://localhost:8443`. The API client defaults to `http://127.0.0.1:8000`; set `VITE_API_BASE_URL` when using a different backend origin.

## Configuration reference

Use the root and backend example files as templates. The names below come from the application source; do not use real values in committed files.

| Variable | Where | Required/use |
| --- | --- | --- |
| `VITE_FIREBASE_API_KEY` | Frontend build | Required for Firebase Web App initialization. Public Web App configuration, not a Firebase Admin credential. |
| `VITE_FIREBASE_AUTH_DOMAIN` | Frontend build | Required Firebase Web App auth domain. |
| `VITE_FIREBASE_PROJECT_ID` | Frontend build | Required Firebase project ID. |
| `VITE_FIREBASE_APP_ID` | Frontend build | Required Firebase Web App ID. |
| `VITE_API_BASE_URL` | Frontend build | Optional; backend API origin, defaults to `http://127.0.0.1:8000`. |
| `FIREBASE_CREDENTIALS_PATH` | Backend | Optional path to Firebase Admin service-account JSON; defaults to `backend/firebase-credentials.json`. The file must remain private. |
| `PRIVORA_CORS_ORIGINS` | Backend | Comma-separated allowed frontend origins; local defaults include ports 8443 and 5173 on localhost/127.0.0.1. Set exact production origins. |
| `DATABASE_URL` | Backend | Optional for active Firestore routes; needed for retained SQLAlchemy/Alembic database operations. |
| `PRIVORA_GMAIL_CLIENT_ID` | Backend | Required to start Gmail OAuth. Google Cloud OAuth Web client ID. |
| `PRIVORA_GMAIL_CLIENT_SECRET` | Backend | Required to exchange OAuth authorization codes. Store as a backend secret. |
| `PRIVORA_GMAIL_REDIRECT_URI` | Backend | Required exact OAuth callback URI registered in Google Cloud. |
| `PRIVORA_GMAIL_TOKEN_ENCRYPTION_KEY` | Backend | Required Fernet key to encrypt Gmail credentials stored in Firestore. Generate with the command below and store in a secret manager. |
| `PRIVORA_FRONTEND_URL` | Backend | Frontend origin used after OAuth callback; defaults to `http://localhost:8443`. |
| `PRIVORA_MAX_EMAILS` | Backend discovery | Optional bound for Gmail metadata scanning; defaults to 100 and provider code caps each scan at 100. |

Generate a Fernet key locally (do not commit or share the output):

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`PRIVORA_ENABLE_EMAIL_DISCOVERY`, `PRIVORA_ENABLE_IDENTITY_VAULT`, `PRIVORA_MAX_EMAIL_BODY_LENGTH`, and `NVIDIA_API_KEY` appear in configuration or legacy code but are not required by the currently active Gmail metadata, analysis, or assistant routes. Do not assume setting them enables additional active integrations.

## Google OAuth setup

Gmail is optional. Synthetic sample discovery does not require Google authorization. To enable the existing Gmail workflow:

1. In Google Cloud, select the intended project and enable the **Gmail API**.
2. Configure the OAuth consent screen, app branding, support details, and a testing audience. Add authorized test-user accounts while the consent screen is in testing.
3. Create an OAuth client ID of type **Web application**.
4. Add local frontend origins `http://localhost:8443` and, if used, `http://127.0.0.1:8443` as authorized JavaScript origins. Add any alternate Vite origin only if you run the app there.
5. Set the backend callback URI exactly to `http://127.0.0.1:8000/discovery/gmail/callback` for the documented local backend command. Register that exact URI as an authorized redirect URI and set the same value in `PRIVORA_GMAIL_REDIRECT_URI`.
6. Set `PRIVORA_FRONTEND_URL` to `http://localhost:8443` and configure the OAuth client ID/secret and Fernet encryption key on the backend. Set CORS origins to the frontend origins you actually use.
7. In the Google consent-screen data-access configuration, declare the scopes requested by the application:
   - `https://www.googleapis.com/auth/gmail.metadata` for bounded message/thread metadata reads used by discovery and reply-candidate checks.
   - `https://www.googleapis.com/auth/gmail.send` for user-approved deletion-request emails.

The code requests both Gmail scopes together when initiating Gmail authorization. It does not request `openid`, `userinfo.email`, or `userinfo.profile` in this Gmail flow. Existing connections may need to reconnect after scope changes. Gmail metadata is a restricted scope and Gmail send is sensitive; Google may require scope verification and additional review/security assessment for public release. Do not claim Google approval before it is granted. Production JavaScript origins, callback URI, and frontend return origin must be configured separately using the final HTTPS domains.

## Using the application

1. Create an account or sign in using Firebase Authentication.
2. Open the account area and either load clearly labelled synthetic samples or connect Gmail and authorize the requested scopes.
3. Run discovery and review service candidates along with their evidence and confidence. Gmail candidates are inferred from headers and are not verified accounts.
4. Open an account to review recorded/inferred categories, activity evidence, local sensitivity analysis, and deterministic recommendations.
5. Ask the account-aware assistant questions about that account. Responses are generated by local rules and are persisted as account-specific chat history.
6. Where a supported deletion channel exists, draft a request and review it. Approval does not send the request. For eligible email channels, sending requires a separate explicit confirmation and a successful Gmail API response. A send confirmation means Gmail accepted the submission; it does not establish provider receipt or deletion.
7. Track requests and replies. User-entered statuses are labelled as user-reported; possible Gmail replies found from thread headers require user confirmation.

## Privacy and limitations

- Gmail discovery reads bounded metadata headers (sender, subject, and date) and does not read email bodies for discovery. Gmail metadata may suggest a service association, not account ownership or present activity.
- Gmail-inferred data categories can be incomplete or wrong. Recorded categories describe data records currently in Privora, not verified provider holdings.
- Sensitivity analysis and recommendations use local heuristics/rules. Review results before acting; they are not legal advice or a provider-side audit.
- The current analysis and chatbot routes use mock/local output; they do not send account context to NVIDIA or another AI provider.
- Gmail OAuth credentials are encrypted in Firestore using the configured Fernet key. Firebase Admin access uses a private credential file. Protect both and grant only the needed hosting/IAM access.
- The application does not currently provide an in-app Gmail disconnect or complete account/data-erasure workflow. A user can revoke Gmail access through their Google Account settings; stored Privora data may require administrator/database handling.
- A deletion request being drafted, approved, sent, or marked replied does not mean an account was deleted. Provider-side deletion must be confirmed with the service.
- No production deployment, live Firebase project, live Gmail authorization, or provider deletion has been verified here.

## Tests and checks

From `backend/`:

```powershell
python -m pytest -q
```

From the repository root:

```powershell
pnpm exec tsc --noEmit -p tsconfig.json
pnpm run build
```

Backend tests include mocked Firebase authentication, Firestore behavior, Gmail OAuth/provider flows, and local API logic. They do not substitute for a live Firebase or Gmail integration test. A previous Windows/Python 3.14 `TestClient` run hung; the cause was not conclusively established as an application defect. For the full suite, use a compatible Python 3.12 environment and impose a process timeout when diagnosing a hang rather than treating a timed-out run as a pass.

## Contributing

Create a focused branch, make a small change, run the relevant checks above, and open a pull request describing the change and its verification. Avoid committing credentials, local `.env` files, user data, or generated secrets. No separate contribution policy is currently defined.

## License and acknowledgements

The repository root contains the standard [MIT License](LICENSE), an [OSI-approved license](https://opensource.org/license/mit). The existing copyright holder and year in `LICENSE` are preserved. The MIT terms do not replace the licenses of third-party libraries, tools, or assets; review their own license notices before redistribution. This README does not claim ownership of third-party material or identify a separate project contact.
