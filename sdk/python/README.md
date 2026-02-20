# AI Home CoPilot Python SDK

Client SDK for the AI Home CoPilot Core API.

## Installation

```bash
pip install ai-home-copilot-sdk
```

Or from source:

```bash
git clone https://github.com/GreenhillEfka/Home-Assistant-Copilot.git
cd Home-Assistant-Copilot/sdk/python
pip install -e .
```

## Usage

```python
from copilot_sdk import CoPilotClient, get_client

# Quick start
client = get_client(
    base_url="http://homeassistant.local:8123/api/copilot",
    auth_token="your-token"
)

# Get system health
health = client.get_system_health()

# Get mood context
mood = client.get_mood_context()

# Submit an event
event_id = client.submit_event("user_action", {"action": "light_on"})

# Get Habitus rules
rules = client.get_habitus_rules()

# Close connection
client.close()
```

Or use context manager:

```python
with get_client() as client:
    mood = client.get_mood_context()
    print(f"Current mood: {mood}")
```

## Environment Variables

- `COPILOT_API_URL`: Base URL of the API (default: `http://homeassistant.local:8123/api/copilot`)
- `COPILOT_AUTH_TOKEN`: Authentication token (optional)

## API Endpoints

- `GET /api/v1/system/health` - System health status
- `GET /api/v1/mood/context` - Current mood context
- `GET /api/v1/graph/visualization` - Brain graph data
- `POST /api/v1/events` - Submit event
- `GET /api/v1/habitus/rules` - Discovered Habitus rules
- `GET /api/v1/tags/registry` - Tag registry

## Testing

```bash
python -m unittest discover tests
```
