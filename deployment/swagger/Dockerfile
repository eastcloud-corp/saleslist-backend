# Prism Mock Server for Render.com
FROM stoplight/prism:4

# OpenAPI仕様書をコピー（デフォルトの作業ディレクトリを使用）
COPY openapi.yaml /tmp/openapi.yaml
COPY examples /tmp/examples

# Renderのポート要件に対応
EXPOSE 10000

# Prismを起動（フルパスでファイルを指定）
CMD ["mock", "-h", "0.0.0.0", "-p", "10000", "/tmp/openapi.yaml"]