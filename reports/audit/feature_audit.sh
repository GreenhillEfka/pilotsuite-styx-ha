#!/bin/bash
echo "# Feature Audit - AI Home CoPilot"
echo "Generiert: $(date)"
echo ""

HACS="ai_home_copilot_hacs_repo/custom_components/ai_home_copilot"
ADDON="addons/copilot_core/rootfs/usr/src/app/copilot_core"

echo "## 1. MODULE IM ADD-ON"
echo "| Modul | Dateien |"
echo "|-------|---------|"
for dir in $(ls -d $ADDON/*/ 2>/dev/null | grep -v __pycache__ | grep -v tests); do
    name=$(basename $dir)
    count=$(find $dir -name "*.py" 2>/dev/null | wc -l)
    echo "| $name | $count |"
done
echo ""

echo "## 2. MODULE IN DER INTEGRATION (hacs_repo)"
echo "| Kategorie | Dateien |"
echo "|-----------|---------|"
for pattern in "button*.py" "sensor*.py" "context*.py" "*_dashboard*.py" "*_entities*.py" "*_store*.py"; do
    count=$(find $HACS -name "$pattern" 2>/dev/null | wc -l)
    if [ $count -gt 0 ]; then
        echo "| $pattern | $count |"
    fi
done
echo ""

echo "## 3. API-ENDPUNKTE IM ADD-ON"
echo "| Endpunkt | Datei |"
echo "|----------|-------|"
grep -r "@blueprint\|@app.route\|@api.route" $ADDON/api/ 2>/dev/null | grep -v __pycache__ | head -30
echo ""

echo "## 4. PORTS IN BEIDEN"
echo "| Datei | Port |"
echo "|-------|------|"
grep -rn "8099\|8909\|5000" $HACS --include="*.py" 2>/dev/null | grep -v __pycache__ | grep -E "= [0-9]{4}|: [0-9]{4}" | head -20
grep -rn "8099\|8909\|5000" $ADDON --include="*.py" 2>/dev/null | grep -v __pycache__ | grep -E "= [0-9]{4}|: [0-9]{4}" | head -10
