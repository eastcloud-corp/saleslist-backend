# Prism Mock Server for Render.com
FROM stoplight/prism:4

# OpenAPI仕様書をコピー
COPY openapi.yaml /openapi.yaml
COPY examples /examples

# Renderのポート要件に対応
EXPOSE 10000

# Prismを起動
CMD ["mock", "-h", "0.0.0.0", "-p", "10000", "/openapi.yaml"]