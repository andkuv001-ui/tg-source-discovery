# Telegram Source Discovery Engine

Automatically discovers, analyzes, and ranks Telegram groups/channels matching a specified topic, geography, language, and commercial intent.

## Architecture

```
tg-source-discovery/
├── backend/                  # FastAPI + Celery + Telethon
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint
│   │   ├── config.py         # Settings (dotenv)
│   │   ├── database.py       # SQLAlchemy async engine
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── api/              # REST endpoints
│   │   ├── services/         # Business logic
│   │   │   ├── query_understanding.py  # LLM + regex extraction
│   │   │   ├── query_expansion.py      # Search query generation
│   │   │   ├── discovery/              # Provider plugins
│   │   │   ├── analysis/               # Source analyzers
│   │   │   ├── scoring.py              # Multi-factor scoring
│   │   │   └── telegram_collector.py   # Telethon data collection
│   │   ├── tasks/            # Celery async tasks
│   │   └── llm/              # RouterAI (OpenAI-compatible)
│   ├── alembic/              # PostgreSQL migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # Next.js + Tailwind
│   ├── src/
│   │   ├── app/              # Pages (App Router)
│   │   └── lib/api.ts        # API client
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Stack

- **Backend**: Python 3.11, FastAPI, Celery, Redis, SQLAlchemy + asyncpg
- **Database**: PostgreSQL (self-hosted Supabase) + pgvector
- **Telegram**: Telethon (MTProto)
- **LLM**: GPT-4o-mini via RouterAI.ru (OpenAI-compatible)
- **Search**: DuckDuckGo (free) with SerpAPI upgrade path
- **Frontend**: Next.js 14, React, Tailwind CSS
- **Deployment**: Docker Compose (Coolify)

## Setup

### 1. Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Docker

```bash
docker-compose up -d
```

### 3. Database Migration

```bash
docker-compose exec backend alembic upgrade head
```

### 4. Frontend

```bash
cd frontend && npm install && npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/projects` | Create project |
| GET | `/api/projects` | List projects |
| GET | `/api/projects/{id}` | Get project |
| POST | `/api/projects/{id}/discover` | Start discovery |
| GET | `/api/projects/{id}/sources` | List scored sources |
| GET | `/api/sources/{id}` | Source detail |
| POST | `/api/sources/{id}/review` | Approve/reject |
| GET | `/api/projects/{id}/graph` | Graph data |
| GET | `/api/projects/{id}/export` | Export CSV/JSON |

## Discovery Pipeline

1. **Query Understanding** — extract topics, geo, language from query (LLM + regex)
2. **Query Expansion** — generate 20-50 search variants
3. **Discovery** — search via DuckDuckGo, TGStat scraping
4. **Collection** — fetch metadata + messages via Telethon
5. **Analysis** — topic, geography, language, audience, intent, activity
6. **Scoring** — multi-factor weighted scoring with configurable profiles
7. **Dedup** — merge sources by telegram_id

## Scoring Profiles

- `lead_generation` — optimized for B2B lead discovery
- `market_research` — broad topic coverage
- `news_monitoring` — active, fresh sources

## Integration with Existing Parser

Export approved sources as CSV/JSON → import into [telegram-audience-parser](../telegram-audience-parser/) for message-level parsing.
