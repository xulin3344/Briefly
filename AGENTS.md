# AGENTS.md - Coding Guidelines for Briefly

This file provides guidelines for agentic coding agents working in this repository.

## Project Overview

Briefly is an AI-powered RSS reader built with:
- **Backend**: FastAPI + Uvicorn + SQLAlchemy (async)
- **Database**: SQLite (aiosqlite)
- **Frontend**: Vanilla JS + Tailwind CSS
- **AI**: OpenAI API / 智谱 AI
- **Scheduling**: APScheduler

---

## Commands

### Python/FastAPI Projects

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run all tests
pytest

# Run a single test file
pytest tests/test_unit.py

# Run a single test
pytest tests/test_unit.py::test_config_settings -v

# Run with coverage
pytest --cov=app --cov-report=html
```

---

## Code Style

### Python

**Imports:**
- Use absolute imports within packages: `from app.models import RSSSource`
- Group imports: stdlib, third-party, local (each group separated by blank line)
- Use `__all__` in `__init__.py` files for public exports

**Formatting:**
- Use 4 spaces for indentation (no tabs)
- Max line length: 88-100 characters
- Use double quotes for docstrings, single quotes acceptable for strings

**Types:**
- Use type hints for all function parameters and return values
- Use `typing` module: `from typing import List, Dict, Optional, Union`
- Use Pydantic models for data validation
- Prefer `str | None` over `Optional[str]` (Python 3.10+)

**Naming:**
- `PascalCase` for classes: `class StockMonitor:`
- `snake_case` for functions/variables: `def get_stock_info():`
- `SCREAMING_SNAKE_CASE` for constants: `MAX_RETRY = 3`
- `snake_case` for modules: `stock_service.py`

**Error Handling:**
- Use specific exceptions, not bare `except:`
- Always log errors with context before re-raising
- Use FastAPI's HTTPException for API errors
- Structure: try/except/finally with proper cleanup

**Async:**
- Use `async def` for I/O operations (DB, HTTP)
- Use `await` consistently
- Use `asynccontextmanager` for lifespan management

### React/TypeScript

**Imports:**
- Use named imports for React hooks: `import { useState, useEffect } from 'react'`
- Group imports: React, third-party, local components, types
- Use path aliases: `@/components/Button`

**Formatting:**
- 2 spaces for indentation
- Semicolons required
- Single quotes for strings
- Trailing commas in objects/arrays

**Types:**
- Use `.ts` for utilities, `.tsx` for components
- Define interfaces for props: `interface ButtonProps { label: string }`
- Use explicit return types for utilities
- Avoid `any`, use `unknown` with type guards

**Naming:**
- `PascalCase` for components: `function StockCard()`
- `camelCase` for functions/variables: `const fetchData`
- `PascalCase` for interfaces/types: `interface StockData`
- `SCREAMING_SNAKE_CASE` for constants: `const API_URL`

---

## Project Structure

### Python FastAPI
```
app/
├── __init__.py
├── main.py              # FastAPI app, lifespan
├── config.py            # Settings with pydantic-settings
├── models/              # SQLAlchemy models
│   ├── database.py      # DB initialization
│   ├── rss_source.py   # RSS source model
│   ├── article.py       # Article model
│   ├── keyword.py       # Keyword filter model
│   ├── webhook_config.py # Webhook config model
│   └── ai_settings.py  # AI settings model
├── routes/              # API routers
│   ├── sources.py       # RSS source endpoints
│   ├── articles.py      # Article endpoints
│   ├── keywords.py     # Keyword endpoints
│   ├── webhook.py      # Webhook endpoints
│   └── system.py       # System/health endpoints
├── services/            # Business logic
│   ├── rss_service.py  # RSS fetching
│   ├── keyword_service.py
│   ├── ai_service.py   # AI summarization
│   ├── scheduler_service.py
│   ├── webhook_service.py
│   └── webhook_scheduler.py
├── core/               # Logging, utilities
│   └── logging.py
└── static/             # Frontend files
    ├── index.html
    ├── config.html
    └── api.js
tests/
├── conftest.py          # Fixtures
├── test_unit.py         # Unit tests
└── test_api.py          # Integration tests
```

---

## Testing Guidelines

- Write tests for business logic
- Use descriptive test names: `test_user_can_login_with_valid_credentials`
- One assertion per test (ideally)
- Use fixtures for setup/teardown
- Mock external services (DB, HTTP, APIs)
- Aim for >70% coverage on critical paths

---

## Documentation

- Docstrings for all public functions/classes
- Use Google/NumPy style docstrings
- README with setup instructions
- API docs auto-generated via FastAPI

---

## Environment & Secrets

- Use `.env` for configuration (never commit secrets)
- Use `pydantic-settings` for environment validation
- Check `.env.example` for required variables
- Never hardcode API keys or credentials

---

## Git

- Write clear commit messages
- Do not commit: `.env`, `node_modules/`, `__pycache__/`, `*.db`
- Use `.gitignore` templates
- Verify with `git status` before committing

---

## Security

- Never expose secrets in code
- Validate all inputs (Pydantic, zod)
- Use parameterized queries (SQLAlchemy)
- Sanitize user inputs
- Enable CORS only for specific origins

---

## Key Files to Know

- `app/main.py` - Application entry point
- `app/config.py` - Configuration management
- `app/models/database.py` - Database setup
- `app/routes/webhook.py` - Webhook API endpoints
- `app/services/webhook_service.py` - Webhook business logic
- `app/services/webhook_scheduler.py` - Scheduled push tasks
- `app/static/config.html` - Configuration frontend page

---

## Database

- Uses SQLite with SQLAlchemy ORM (async)
- Default location: `data/briefly.db`
- When adding new models, ensure they're imported in `app/models/__init__.py` and `app/models/database.py::init_db()`
- Delete `data/briefly.db` to reset the database (for development)
