#!/bin/bash
# Simple OpenAPI merge script

echo "🔧 Merging OpenAPI files..."

# Merge main and schemas back to single file
cat openapi-main.yaml > openapi-merged.yaml
echo "" >> openapi-merged.yaml
tail -n +2 openapi-schemas.yaml >> openapi-merged.yaml

echo "✅ Merged to openapi-merged.yaml"
echo "📊 Size: $(wc -l openapi-merged.yaml | cut -d' ' -f1) lines"

# Validate if Python available
if command -v python3 &> /dev/null; then
    python3 -c "import yaml; yaml.safe_load(open('openapi-merged.yaml'))" 2>/dev/null && \
        echo "✅ Valid YAML" || echo "❌ Invalid YAML"
fi