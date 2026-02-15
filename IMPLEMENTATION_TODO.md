# Missing Core API Endpoints - Implementation Todo

## Endpoints to Implement

1. `/api/v1/status` - System Health Check
2. `/api/v1/capabilities` - Feature Discovery (already exists)
3. `/api/v1/vector/*` - Vector Operations (5 endpoints)
4. `/api/v1/dashboard/brain-summary` - Dashboard Data

## Progress

- [ ] Create `/api/v1/status` endpoint
- [ ] Create `/api/v1/vector` directory structure
- [ ] Implement vector_store API endpoints (5 endpoints)
- [ ] Create `/api/v1/dashboard/brain-summary` endpoint
- [ ] Test all new endpoints

## Implementation Details

### Status Endpoint
- Should return system health information
- Similar to `/health` but under `/api/v1/` prefix

### Vector Store Endpoints (5)
1. POST `/api/v1/vector/store` - Store a vector
2. GET `/api/v1/vector/search` - Search similar vectors
3. GET `/api/v1/vector/get/:id` - Get a specific vector
4. DELETE `/api/v1/vector/:id` - Delete a vector
5. GET `/api/v1/vector/stats` - Get vector store statistics

### Dashboard Brain Summary
- Return brain graph summary data for dashboard display
