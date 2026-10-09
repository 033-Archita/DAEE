# Daily Curiosity Agent

Daily Curiosity Agent is a small editorial AI workflow that turns a daily stream of public topics into a polished email with three mini-lessons and a short news briefing. The goal is not to sound like a generic AI summary; the goal is to feel like a thoughtful digital publication.

## What the project does

The app is built around a simple daily loop:

- generate or refill a topic pool
- pick a few topics for the day
- research each topic
- produce a structured curiosity story with a hook, sections, takeaway, and sources
- prepare a short current-events summary
- render a Gmail-friendly HTML email
- send the email once per day with idempotent safeguards

It includes:

- configuration and environment validation
- MongoDB Atlas-backed state storage with Redis-style compatibility wrappers
- provider-independent LLM routing
- structured topic selection and deduplication
- research + story generation
- HTML email rendering with a publication-style design
- Gmail integration
- demo mode for local visual checks

## Quick start

### 1) Create the environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 2) Configure your environment

Create a `.env` file in the project root with values like:

```dotenv
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGO_DATABASE=daily_curiosity
APP_ENV=development
LOG_LEVEL=INFO
TIMEZONE=Asia/Kolkata
GROQ_API_KEY=your-groq-key
MISTRAL_API_KEY=your-mistral-key
TAVILY_API_KEY=your-tavily-key
GMAIL_OAUTH_CLIENT_ID=your-google-client-id
GMAIL_OAUTH_CLIENT_SECRET=your-google-client-secret
GMAIL_REFRESH_TOKEN=your-gmail-refresh-token
GMAIL_RECIPIENT=you@example.com
```

Notes:

- The app currently expects MongoDB Atlas as the main persistent store.
- It accepts a Redis-style URI field as compatibility input, but the project is intentionally migrated to MongoDB Atlas.
- Keep all secrets in `.env` and do not commit them.

### GitHub Actions secrets for daily email

The repository includes a scheduled GitHub Actions workflow that runs daily at 10:00 Asia/Kolkata and can also be started manually from the Actions tab. To enable actual delivery, open the GitHub repository's **Settings → Secrets and variables → Actions** and add these repository secrets:

- `MONGO_URI`
- `GROQ_API_KEY` and/or `MISTRAL_API_KEY` (at least one configured provider)
- `TAVILY_API_KEY`
- `GMAIL_OAUTH_CLIENT_ID`
- `GMAIL_OAUTH_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`
- `GMAIL_RECIPIENT`

The Gmail refresh token must be authorized for the Gmail account used to send the email, and the recipient must be an address that account is allowed to send to. Never put secret values in workflow YAML, README files, or `.env.example`. After adding the secrets, use **Actions → Daily Curiosity → Run workflow** for the first delivery check; subsequent runs use the daily schedule.

### 3) Validate the app

```powershell
python -m app.main --check
```

This checks configuration and MongoDB connectivity without running the full workflow.

### 4) Run the test suite

```powershell
python -m pytest
```

### 5) Render a demo email locally

```powershell
python -m app.main --demo --demo-output .\demo-output.html
```

This writes a sample HTML email to disk so you can inspect the layout without calling external APIs.

### 6) Run the real daily workflow

```powershell
python -m app.main
```

This runs the full pipeline: topics, research, story generation, email rendering, and Gmail delivery when credentials are configured.

## Project structure

```text
app/
  bootstrap.py         assembles the runtime services and Mongo-backed repository
  config.py            environment-backed settings and validation
  logging_config.py    structured logging
  memory/
    mongo.py           MongoDB Atlas repository with Redis-like semantics
    redis.py           compatibility layer for older imports and tests
    health.py          provider health and cooldown tracking
  llm/                 provider abstraction and router
  topics/              topic selection, deduplication, and pool logic
  research/            web research and structured briefs
  story/               editorial story generation and structured models
  news/                last-24-hours briefing
  email/               HTML rendering and Gmail sender
  orchestration/       daily workflow and delivery orchestration
  main.py              CLI entry point
```

## How the daily flow works

1. Configuration is loaded from `.env`.
2. MongoDB Atlas is connected and used as the persistence layer.
3. The topic pool is checked and refilled when needed.
4. A few topics are reserved for the day.
5. Each topic is researched from search results and context.
6. A structured curiosity story is generated with a hook, sections, takeaway, and sources.
7. A short news summary is assembled from recent developments.
8. The final HTML email is rendered with editorial styling.
9. Gmail sends the message once when configured.
10. The run state is stored so retries remain safe and idempotent.

## Storage and compatibility notes

The project now uses MongoDB Atlas as its canonical persistence layer, but a compatibility layer still exposes older Redis-like semantics used by the application code.

This means:

- the app expects `MONGO_URI` and `MONGO_DATABASE`
- a legacy `REDIS_URL` value is still accepted for transition compatibility
- the repository layer intentionally behaves like a small Redis API to keep the rest of the app stable

## Required providers

The app can work with:

- Groq for LLM generation
- Mistral for model fallback or alternate routing
- Tavily for search/research
- Gmail OAuth for sending the final email

Demo mode can run without external providers.

## Editorial design goals

The output is meant to feel like a digital editorial publication rather than a raw AI digest. The current design emphasizes:

- warm parchment backgrounds
- teal or journal-style structure accents
- clear headline hierarchy
- readable narrative sections
- source lists separated from the main body
- a short rabbit-hole question that invites curiosity

## Local documentation

`LOCAL_PROJECT_GUIDE.md` is excluded from Git and remains available only in the local workspace.

## Security

- Keep `.env` local.
- Never commit API keys or Gmail OAuth secrets.
- Avoid logging secret values.
- Use a secure secret store in production deployments.

## Useful commands

```powershell
python -m pytest
python -m app.main --check
python -m app.main --demo --demo-output .\demo-output.html
```
