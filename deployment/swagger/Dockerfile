# Prism Mock Server for Render.com
FROM stoplight/prism:4

# OpenAPI仕様書をコピー
COPY ./openapi.yaml /swagger/openapi.yaml
COPY ./examples /swagger/examples

# Renderのポート要件に対応
EXPOSE 10000

# Prismを起動（成功例と同じ設定）
# --cors でCORS有効化
# --errors=false で認証エラーを無効化（モック環境用）
ENTRYPOINT ["prism"]
CMD ["mock", "-h", "0.0.0.0", "-p", "10000", "--cors", "/swagger/openapi.yaml"]