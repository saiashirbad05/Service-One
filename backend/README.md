# Service-One Backend

This is the FastAPI backend service for the Service-One appliance repair price verification platform.

---

## 🚀 Key Architectural Features Implemented

1. **Pydantic Settings Management**: Environment variables (e.g. `DATABASE_URL`, models, API keys) are safely loaded, validated, and managed via `config.py` using `pydantic-settings`.
2. **PostgreSQL Persistence**: The backend local database is run via `docker-compose` with persistent volume mount bindings (`pgdata`) preventing accidental database losses.
3. **Database Initialization & Seeding**: A setup script `db/init_db.py` runs the schema definitions and seeds regional pricing signals, localities, and providers automatically.
4. **Structured Logging**: Request traces, agent latency, and database query latency tracking are structured and logged via standard Python `logging`.
5. **Robust Fallback Estimations**: If real-time agent/ADK pipelines encounter errors, the API handles the request gracefully via local fallback pricing estimates (preventing 500 server crashes).
6. **Model Context Protocol (MCP) Server**: Exposes local pricing bounds, provider directories, crowdsourced reports, and geolocation PIN lookup tools via an standard FastMCP server (`mcp_server.py`).
7. **System Healthz**: An active health verification endpoint `/healthz` checks database socket connectivity.
8. **Unit Tests**: Full verification suite using `pytest` covering agents and API endpoints.

---

## 🛠️ Local Setup & Orchestration

### Prerequisites
* Docker & Docker Compose
* Python 3.11+

### 1. Environment Configuration
Copy the default environment template and supply your values:
```bash
cp .env.example .env
```

### 2. Run Database & Application via Docker
Launch the Postgres database container with persistent mounts and build the FastAPI web service:
```bash
docker-compose up --build
```
The database exposed on port `5432` will persist data under the local `pgdata` volume.

### 3. Initialize & Seed Database (First Run)
To run schema migrations and populate pricing signals, run:
```bash
# In your virtual environment
python db/init_db.py
```

### 4. Running the Model Context Protocol (MCP) Server
To run the standard stdio MCP server for agentic integrations:
```bash
python mcp_server.py
```

---

## 🧪 Testing
Run the complete unit test suite using `pytest`:
```bash
pytest -v
```
The tests check the geolocations, agent workflows, `/healthz` checks, and verify that mock fallbacks trigger correctly when services error.
