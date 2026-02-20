## 🌐 UniFi Context Module

Network monitoring context for AI Home CoPilot — connects Core Add-on UniFi Neuron to HA Integration.

### What's New
- **6 new sensor entities** for network monitoring
- WAN status (online, latency, packet loss, uptime)
- Connected clients count
- Roaming activity detection

### Entities Added
| Entity | Type | Description |
|--------|------|-------------|
| `sensor.ai_home_copilot_unifi_clients_online` | Sensor | Online clients count |
| `sensor.ai_home_copilot_unifi_wan_latency` | Sensor | WAN latency (ms) |
| `sensor.ai_home_copilot_unifi_packet_loss` | Sensor | WAN packet loss (%) |
| `binary_sensor.ai_home_copilot_unifi_wan_online` | Binary | WAN connectivity |
| `binary_sensor.ai_home_copilot_unifi_roaming` | Binary | Recent roaming |
| `sensor.ai_home_copilot_unifi_wan_uptime` | Sensor | WAN uptime |

### Technical
- Connects to Core Add-on UniFi Neuron v0.4.10
- Privacy-first: only aggregated network data
- Follows EnergyContext/MoodContext module pattern

### Files Changed
- `custom_components/ai_home_copilot/unifi_context.py`
- `custom_components/ai_home_copilot/unifi_context_entities.py`
- `custom_components/ai_home_copilot/core/modules/unifi_context_module.py`
- `custom_components/ai_home_copilot/__init__.py`
- `CHANGELOG.md`
