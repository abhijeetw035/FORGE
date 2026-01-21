# FORGE

Code Entropy Engine - A sophisticated AST-based repository analysis tool that visualizes code complexity and churn patterns.

## Features

- 🔍 Multi-language AST parsing (Python, JavaScript, Java, Go)
- 📊 Interactive entropy heatmaps
- 🔥 Code churn analysis
- 🎯 Risk assessment visualization
- 🔐 Private repository support via GitHub tokens

## Architecture

- **API**: FastAPI service for REST endpoints
- **Miner**: Python worker for Git and AST analysis  
- **Dashboard**: Next.js visualization layer
- **Storage**: Volume for cloned repositories

## Services

- PostgreSQL: Database
- Redis: Task queue
- API: Port 8000
- Dashboard: Port 3000

## Quick Start

### 1. Setup Environment

```bash
cp .env.example .env
```

Edit `.env` and add your GitHub token for private repository access:
```bash
GITHUB_TOKEN=ghp_your_token_here
```

**Getting a GitHub Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Copy token to `.env` file

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Submit Repository for Analysis

```bash
curl -X POST http://localhost:8000/repositories/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/your-org/your-repo"}'
```

### 4. View Dashboard

Open `http://localhost:3000` to see the entropy heatmap!

## Development

```bash
docker-compose up
```

## API Endpoints

- `POST /repositories/` - Queue repository for analysis
- `GET /repositories/` - List all repositories
- `GET /repositories/{id}` - Get repository details
- `DELETE /repositories/{id}` - Delete repository
- `GET /analytics/repositories/{id}/heatmap` - Get code churn heatmap data
