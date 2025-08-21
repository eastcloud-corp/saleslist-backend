#!/bin/bash

# OpenAPI分割ファイルを統合してデプロイ用ファイルを生成
# Usage: ./bundle.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENAPI_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_FILE="$OPENAPI_DIR/../openapi-bundled.yaml"

echo "🔧 OpenAPI Bundle Script"
echo "========================"
echo "Source: $OPENAPI_DIR"
echo "Output: $OUTPUT_FILE"
echo ""

# 1. メインファイルのヘッダー部分をコピー
echo "📝 Writing header..."
sed -n '1,/^paths:/p' "$OPENAPI_DIR/openapi.yaml" > "$OUTPUT_FILE"

# 2. 各pathsファイルの内容を結合
echo "📁 Merging paths..."

# Auth
if [ -f "$OPENAPI_DIR/paths/auth.yaml" ]; then
    echo "  - auth.yaml"
    sed -n '/^  \/auth/,/^[^ ]/p' "$OPENAPI_DIR/paths/auth.yaml" | sed '$d' >> "$OUTPUT_FILE"
fi

# Companies (複数ファイル対応)
for file in "$OPENAPI_DIR/paths/companies"/*.yaml; do
    if [ -f "$file" ]; then
        echo "  - $(basename "$file")"
        sed -n '/^  \//,/^[^ ]/p' "$file" | sed '$d' >> "$OUTPUT_FILE"
    fi
done

# Projects
if [ -f "$OPENAPI_DIR/paths/projects.yaml" ]; then
    echo "  - projects.yaml"
    sed -n '/^  \//,/^[^ ]/p' "$OPENAPI_DIR/paths/projects.yaml" | sed '$d' >> "$OUTPUT_FILE"
fi

# Clients
if [ -f "$OPENAPI_DIR/paths/clients.yaml" ]; then
    echo "  - clients.yaml"
    sed -n '/^  \//,/^[^ ]/p' "$OPENAPI_DIR/paths/clients.yaml" | sed '$d' >> "$OUTPUT_FILE"
fi

# Master
if [ -f "$OPENAPI_DIR/paths/master.yaml" ]; then
    echo "  - master.yaml"
    sed -n '/^  \//,/^[^ ]/p' "$OPENAPI_DIR/paths/master.yaml" | sed '$d' >> "$OUTPUT_FILE"
fi

# 3. Components部分を追加
echo "📦 Adding components..."
echo "" >> "$OUTPUT_FILE"
echo "components:" >> "$OUTPUT_FILE"

# Security schemes
sed -n '/^  securitySchemes:/,/^  [^ ]/p' "$OPENAPI_DIR/openapi.yaml" | sed '$d' >> "$OUTPUT_FILE"

# Schemas
if [ -f "$OPENAPI_DIR/schemas/all.yaml" ]; then
    echo "  - schemas/all.yaml"
    cat "$OPENAPI_DIR/schemas/all.yaml" >> "$OUTPUT_FILE"
fi

# 4. 検証
echo ""
echo "✅ Bundle complete!"
echo "📊 File size: $(wc -l "$OUTPUT_FILE" | cut -d' ' -f1) lines"

# YAMLの構文チェック (Pythonがあれば)
if command -v python3 &> /dev/null; then
    echo "🔍 Validating YAML syntax..."
    python3 -c "import yaml; yaml.safe_load(open('$OUTPUT_FILE'))" && echo "✅ YAML syntax is valid!" || echo "❌ YAML syntax error!"
fi

echo ""
echo "📦 Output file: $OUTPUT_FILE"
echo "🚀 Ready for deployment!"