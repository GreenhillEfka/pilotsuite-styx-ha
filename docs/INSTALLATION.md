# AI Home CoPilot Installation Guide

## Prerequisites

- Home Assistant Core 2024.12+ or Home Assistant OS
- Python 3.11+ (for add-on development)
- Node.js 18+ (for TypeScript SDK)

## Installation Methods

### Method 1: HACS (Recommended for Integration)

1. **Install HACS** (if not already installed)
   - Visit [hacs.xyz](https://hacs.xyz)
   - Follow the installation instructions

2. **Add Custom Repository**
   - Open HACS → Integrations
   - Click the three dots menu (⋮)
   - Select "Custom repositories"
   - Add repository URL: `https://github.com/GreenhillEfka/ai-home-copilot-ha`
   - Select type: **Integration**
   - Click "Add"

3. **Install Integration**
   - In HACS → Integrations, search for "AI Home CoPilot"
   - Click "Download" or "Install"
   - Restart Home Assistant

4. **Configure Integration**
   - Go to Settings → Devices & services
   - Click "Add integration"
   - Select "AI Home CoPilot"
   - Configure:
     - **Host**: `homeassistant.local` or your HA IP
     - **Port**: `8909` (default)
     - **API Token**: Optional (if Core has auth enabled)
     - **Test Light**: Optional (for demo)

5. **Verify Installation**
   - Check that `binary_sensor.ai_home_copilot_online` is `on`
   - Verify `sensor.ai_home_copilot_version` shows the correct version

### Method 2: Home Assistant Add-on (Core Service)

1. **Add Add-on Repository**
   - Go to Settings → Add-ons
   - Click Add-on Store
   - Click the three dots menu (⋮)
   - Select "Repositories"
   - Add repository URL: `https://github.com/GreenhillEfka/Home-Assistant-Copilot`
   - Click "Add"

2. **Install Add-on**
   - Find "AI Home CoPilot Core (MVP)"
   - Click to open
   - Review configuration options
   - Click "Install"

3. **Configure Add-on** (optional)
   ```json
   {
     "log_level": "info",
     "auth_token": "your-secret-token",
     "brain_graph": {
       "max_nodes": 500,
       "max_edges": 1500
     }
   }
   ```

4. **Start Add-on**
   - Click "Start"
   - Verify logs show successful startup

5. **Verify Add-on**
   - Open web UI: `http://homeassistant.local:8909/health`
   - Should return: `{"status":"ok","version":"0.6.0"}`

### Method 3: Manual Installation (Development)

#### Integration (HA)

```bash
# Clone repository
git clone https://github.com/GreenhillEfka/ai-home-copilot-ha.git

# Copy to custom components
cp -r ai-home-copilot-ha/custom_components/ai_home_copilot \
    /config/custom_components/

# Restart Home Assistant
```

#### Core Add-on

```bash
# Clone repository
git clone https://github.com/GreenhillEfka/Home-Assistant-Copilot.git

# Build Docker image
cd Home-Assistant-Copilot/addons/copilot_core
docker build -t copilot-core .

# Run container
docker run -d \
  --name copilot-core \
  -p 8909:8909 \
  -v /path/to/data:/data \
  copilot-core
```

## Post-Installation Setup

### 1. Verify Core Connectivity

Check HA logs for successful connection:
```log
INFO [ai_home_copilot] Core connection established
```

### 2. Configure Event Forwarding

The integration automatically forwards events to Core. To customize:

```yaml
# configuration.yaml (optional)
ai_home_copilot:
  host: homeassistant.local
  port: 8909
  token: your-token
  forward_entities:
    - light.*
    - switch.*
    - person.*
```

### 3. Enable Advanced Features

**Multi-User Preferences:**
- Create person entities for each user
- Preferences are automatically collected

**Brain Graph Visualization:**
- Install Lovelace card via HACS
- Add to dashboard: `custom:brain-graph-panel`

**Mood Context:**
- Media context automatically detected
- Zone mood calculated per-area

### 4. Test Installation

**Test Light Button:**
- Integration UI → Toggle test light
- Verify light changes state

**Verify Core API:**
```bash
curl http://homeassistant.local:8909/health
```

**Check Entities:**
- `binary_sensor.ai_home_copilot_online` should be `on`
- `sensor.ai_home_copilot_version` shows version

## Troubleshooting

### Integration Not Connecting

1. Check Core is running: `curl http://localhost:8909/health`
2. Verify network connectivity: `ping homeassistant.local`
3. Check firewall rules: port 8909 must be open
4. Review HA logs: Settings → System → Logs

### Core Not Starting

1. Check add-on logs: Add-ons → CoPilot Core → Logs
2. Verify Docker: `docker ps | grep copilot`
3. Check port conflict: `netstat -tlnp | grep 8909`
4. Verify config: `/data/options.json`

### Events Not Forwarded

1. Check integration logs for errors
2. Verify webhook registration
3. Ensure `http` integration is configured
4. Check entity filters in config

### API Authentication Failures

1. Verify token matches in HA and Core
2. Check token format (no special characters)
3. Ensure `X-Auth-Token` header is included
4. Verify token is set in Core config

## Rolling Back

### HACS

1. HACS → Integrations → AI Home CoPilot
2. Click version dropdown
3. Select previous version
4. Click "Download"

### Add-on

1. Stop add-on
2. Go to Add-ons → CoPilot Core
3. Click three dots → Rollback
4. Select previous version
5. Start add-on

## Uninstallation

### HACS

1. HACS → Integrations
2. Find AI Home CoPilot
3. Click three dots → Remove
4. Restart Home Assistant

### Add-on

1. Stop add-on
2. Click three dots → Uninstall
3. Remove repository from Add-on store

## Support

- **Documentation**: See `/docs/` in both repositories
- **Issues**: GitHub Issues tab
- **Discussions**: GitHub Discussions tab
