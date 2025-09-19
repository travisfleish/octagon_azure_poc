Octagon Staffing Plan Generator (FastAPI)
========================================

FastAPI application integrating Azure services (Blob Storage, Document Intelligence, Azure OpenAI, Azure AI Search) to ingest SOW documents, extract structured data, and generate staffing plan recommendations.

Endpoints
---------
- GET `/health`
- POST `/upload-sow` (multipart, PDF/DOCX only)
- GET `/process-sow/{file_id}`
- GET `/staffing-plan/{sow_id}`
- GET `/sows`

Environment Variables
---------------------
Provide via Azure Container Apps Key Vault references or `.env` in development.
- `STORAGE_BLOB_ENDPOINT`
- `DOCINTEL_ENDPOINT`, `DOCINTEL_KEY`
- `AOAI_ENDPOINT`, `AOAI_KEY`, `AOAI_DEPLOYMENT`, `AOAI_API_VERSION`
- `SEARCH_ENDPOINT`, `SEARCH_KEY`, `SEARCH_INDEX_NAME`
- `ENVIRONMENT`, `PORT`, `LOG_LEVEL`, `CORS_ALLOW_ORIGINS`

Local Development
-----------------
1. Python 3.11
2. `pip install -r requirements.txt`
3. Export environment variables
4. Run: `uvicorn app.main:app --reload --port 8080`

Docker
------
Build and run:
```
docker build -t octagon-staffing-app .
docker run -p 8080:8080 --env-file .env octagon-staffing-app
```

Notes
-----
- Async Azure SDK clients are used where available.
- In-memory stores are placeholders; replace with durable storage for production.
- Logging is JSON-structured for Azure Log Analytics.



