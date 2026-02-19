#!/bin/bash
# sync_workspace.sh - Workspace Sync & GitHub Status
# Part of AI Home CoPilot automation

set -e

REPO_HA="/config/.openclaw/workspace/ai_home_copilot_hacs_repo"
REPO_CORE="/config/.openclaw/workspace/ha-copilot-repo"
WORKSPACE="/config/.openclaw/workspace"

echo "=== Workspace Sync $(date '+%Y-%m-%d %H:%M') ==="
echo ""

# Function to sync a repo
sync_repo() {
    local repo_path="$1"
    local repo_name="$2"
    
    echo "--- $repo_name ---"
    cd "$repo_path"
    
    # Check for uncommitted changes
    if git diff --quiet 2>/dev/null && git diff --staged --quiet 2>/dev/null; then
        echo "✅ Clean working tree"
    else
        echo "⚠️ Uncommitted changes detected"
        git status --short
    fi
    
    # Fetch and check for updates
    git fetch origin 2>/dev/null || true
    
    LOCAL=$(git rev-parse HEAD 2>/dev/null)
    REMOTE=$(git rev-parse '@{u}' 2>/dev/null || echo "unknown")
    
    if [ "$LOCAL" = "$REMOTE" ]; then
        echo "✅ Synced with origin"
    else
        echo "📥 Pulling updates..."
        git pull --rebase origin main 2>/dev/null || echo "⚠️ Pull failed - may need manual merge"
    fi
    
    # Show last commit
    echo "Last: $(git log -1 --oneline)"
    echo ""
}

# Sync both repos
sync_repo "$REPO_HA" "HA Integration"
sync_repo "$REPO_CORE" "Core Add-on"

# Check React Board
echo "--- React Board ---"
if curl -s -o /dev/null -w "%{http_code}" "http://${REACTBOARD_HOST:-localhost}:48099/__openclaw__/ReactBoard/" | grep -q "200"; then
    echo "✅ React Board UP"
else
    echo "⚠️ React Board not responding"
fi
echo ""

# Summary
echo "=== Summary ==="
cd "$REPO_HA"
echo "HA Integration: $(git log -1 --oneline)"
cd "$REPO_CORE"
echo "Core Add-on: $(git log -1 --oneline)"
echo ""
echo "✅ Sync complete"