# FORGE

Code Entropy Engine - A sophisticated AST-based repository analysis tool.

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

## Development

```bash
docker-compose up
```

## API Endpoints

- `POST /repositories/` - Queue repository for analysis
- `GET /repositories/` - List all repositories
- `GET /repositories/{id}` - Get repository details
- `DELETE /repositories/{id}` - Delete repository
