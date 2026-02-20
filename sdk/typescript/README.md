# AI Home CoPilot TypeScript SDK

TypeScript/JavaScript client for AI Home CoPilot Core API.

## Installation

```bash
npm install ai-home-copilot-client
# or
yarn add ai-home-copilot-client
```

## Usage

```typescript
import { CopilotClient } from 'ai-home-copilot-client';

const client = new CopilotClient({
  baseUrl: 'http://localhost:48099',
  authToken: 'your-token-here', // optional
});

// Get habitus status
const status = await client.habitus.getStatus();

// Mine rules from events
const result = await client.habitus.mineRules({
  events: [...]
});

// Get brain graph state
const graph = await client.graph.getState();

// Get neurons
const neurons = await client.neurons.list();

// Get current mood
const mood = await client.neurons.getMood();
```

## API Endpoints

### Habitus
- `GET /api/v1/habitus/status` - Get miner status
- `GET /api/v1/habitus/rules` - Get discovered rules
- `POST /api/v1/habitus/mine` - Mine rules from events
- `GET /api/v1/habitus/dashboard_cards` - Get dashboard cards
- `GET /api/v1/habitus/dashboard_cards/zones` - Get zones

### Graph
- `GET /api/v1/graph/state` - Get brain graph state
- `GET /api/v1/graph/patterns` - Get discovered patterns
- `POST /api/v1/graph/sync` - Sync graph with HA entities

### Neurons
- `GET /api/v1/neurons` - List all neurons
- `GET /api/v1/neurons/{id}` - Get neuron state
- `POST /api/v1/neurons/evaluate` - Run neural evaluation
- `GET /api/v1/neurons/mood` - Get current mood
- `GET /api/v1/neurons/suggestions` - Get suggestions

### Tags
- `GET /api/v1/tags2/tags` - Get all tags
- `POST /api/v1/tags2/tags` - Create tag
- `GET /api/v1/tags2/subjects/{id}/tags` - Get subject tags

### Vector Store
- `POST /api/v1/vector/embeddings` - Create embedding
- `GET /api/v1/vector/similar/{id}` - Find similar entities
- `GET /api/v1/vector/vectors` - List vectors
- `GET /api/v1/vector/stats` - Get stats

## License

MIT