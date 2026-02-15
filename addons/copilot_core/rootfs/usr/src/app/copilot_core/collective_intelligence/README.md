# Collective Intelligence - Phase 5 Implementation

## Overview

This module implements **Phase 5: Collective Intelligence** for the AI Home CoPilot system, enabling distributed learning and knowledge sharing across multiple homes while preserving privacy.

## Architecture

```
collective_intelligence/
├── __init__.py          # Module exports
├── models.py            # Data models (Update, Aggregation, Round, Knowledge)
├── service.py           # Main service coordinator
├── federated_learner.py # Federated learning core
├── model_aggregator.py  # Model aggregation with versioning
├── privacy_preserver.py # Differential privacy mechanisms
└── knowledge_transfer.py # Cross-home knowledge sharing
```

## Components

### 1. Federated Learning (`federated_learner.py`)

Enables **decentralized learning without data sharing**:

- Each home trains locally on its own data
- Only model updates (weights) are shared
- Supports multiple aggregation strategies:
  - `FEDERATED_AVERAGING` (default)
  - `FEDERATED_MEDIAN`
  - `FEDERATED_TRIMMED_MEAN`
  - `WEIGHTED_AVERAGE`

**Usage:**
```python
learner = FederatedLearner()

# Register participants
learner.register_participant("home-001")
learner.register_participant("home-002")

# Start round
round_id = learner.start_round().round_id

# Submit updates
learner.submit_update("home-001", {"weight1": 0.5, "weight2": 0.3})
learner.submit_update("home-002", {"weight1": 0.4, "weight2": 0.2})

# Aggregate
aggregated = learner.aggregate(round_id)
```

### 2. Model Aggregator (`model_aggregator.py`)

Handles **model aggregation with versioning and quality tracking**:

- Multiple aggregation strategies
- Model versioning (timestamp-based)
- Quality assessment from metrics
- Model history and restore

**Features:**
- Automatic version generation
- Quality scoring from metrics
- Backup/restore capabilities
- Participant statistics

### 3. Privacy Preserver (`privacy_preserver.py`)

Implements **differential privacy** for safe aggregation:

- Gaussian noise addition
- Privacy budget tracking per node
- Clip values to bounded norm
- Aggregate with privacy guarantees

**Usage:**
```python
privacy = DifferentialPrivacy(epsilon=1.0, delta=1e-5)

# Add noise to values
noisy_value = privacy.add_gaussian_noise(
    value=10.5,
    sensitivity=1.0
)

# Privacy-aware aggregator
aggregator = PrivacyAwareAggregator(global_epsilon=1.0)
aggregator.register_node("home-001", max_epsilon=1.0)
```

### 4. Knowledge Transfer (`knowledge_transfer.py`)

Enables **cross-home knowledge sharing**:

- Extract knowledge patterns from local data
- Privacy-preserving transfer
- Knowledge validation with confidence scores
- Transfer rate limiting

**Knowledge Types:**
- `habitus_pattern` - Behavioral patterns
- `energy_saving` - Energy optimization tips
- `mood_prediction` - Mood-based recommendations
- Custom types

### 5. Service (`service.py`)

**Main coordinator** integrating all components:

- Orchestrates federated learning rounds
- Manages privacy budgets
- Coordinates knowledge transfer
- Provides system status and statistics

## Data Models

### ModelUpdate
```python
{
    "node_id": "home-001",
    "model_version": "v1.0.0",
    "weights": {"weight1": 0.5, "weight2": 0.3},
    "metrics": {"loss": 0.1, "accuracy": 0.95},
    "timestamp": 1644900000.0,
    "privacy_budget": 1.0
}
```

### AggregatedModel
```python
{
    "model_version": "v1644900000-fed-avg-q0.92",
    "weights": {"weight1": 0.45, "weight2": 0.25},
    "aggregation_method": "fed_avg",
    "participants": ["home-001", "home-002"],
    "metrics": {"loss": 0.12, "accuracy": 0.93}
}
```

### KnowledgeItem
```python
{
    "knowledge_id": "abc123",
    "source_node_id": "home-001",
    "knowledge_type": "habitus_pattern",
    "payload": {"pattern": "morning_routine", "duration": 3600},
    "confidence": 0.85
}
```

## API Endpoints (Planned)

```python
# Federated Learning
POST /api/v1/collective/learner/register
POST /api/v1/collective/learner/update
POST /api/v1/collective/learner/round/start
POST /api/v1/collective/learner/round/aggregate

# Knowledge Transfer
POST /api/v1/collective/knowledge/extract
POST /api/v1/collective/knowledge/transfer
GET  /api/v1/collective/knowledge/base

# Status
GET  /api/v1/collective/status
GET  /api/v1/collective/statistics
```

## Privacy Guarantees

- **Per-node privacy budgets** with configurable epsilon/delta
- **Gaussian noise** added during aggregation
- **Value clipping** to bounded L2 norm
- **No raw data sharing** - only model weights and aggregated knowledge
- **Transfer rate limiting** to prevent re-identification

## Scalability Considerations

- Distributed learning scales linearly with participants
- Aggregation complexity: O(n * d) where n=participants, d=weight dimensions
- Knowledge transfer is O(1) per item
- Privacy budget management is O(1) per node

## Future Enhancements

1. **Secure Multi-Party Computation** for truly private aggregation
2. **Homomorphic Encryption** support
3. **Peer-to-peer federated learning** (without central coordinator)
4. **Cross-domain knowledge transfer**
5. **Federated transfer learning** for pre-trained models

## Testing

Run tests from the app directory:

```bash
cd /config/.openclaw/workspace/ha-copilot-repo/addons/copilot_core/rootfs/usr/src/app
python -m pytest tests/test_collective_intelligence.py
```

## Example Usage

```python
from copilot_core.collective_intelligence import (
    CollectiveIntelligenceService,
    AggregationMethod
)

# Initialize
service = CollectiveIntelligenceService()
service.start()

# Register homes
service.register_node("home-001")
service.register_node("home-002")
service.register_node("home-003")

# Start federated round
round_id = service.start_federated_round()

# Submit updates (simulated)
service.submit_local_update("home-001", {"weights": [0.5, 0.3]})
service.submit_local_update("home-002", {"weights": [0.4, 0.2]})
service.submit_local_update("home-003", {"weights": [0.6, 0.4]})

# Aggregate
aggregated = service.execute_aggregation(round_id)

# Extract and transfer knowledge
knowledge = service.extract_knowledge(
    "home-001",
    "energy_saving",
    {"recommendation": "lower_heating_at_night", "savings_kwh": 15.2},
    confidence=0.88
)

if knowledge:
    service.transfer_knowledge(knowledge.knowledge_id, "home-002")

# Get status
status = service.get_status()
print(f"Completed {status.completed_rounds} rounds with {status.participating_nodes} homes")
```
