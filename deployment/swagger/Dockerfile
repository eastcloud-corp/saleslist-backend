# Prism Mock Server for Render.com
FROM stoplight/prism:4

# 作業ディレクトリを設定
WORKDIR /usr/src/prism

# OpenAPI仕様書をコピー
COPY openapi.yaml .
COPY examples ./examples

# Renderのポート要件に対応
EXPOSE 10000

# Prismを直接起動（動作確認済みのコマンド）
CMD ["mock", "openapi.yaml", "-h", "0.0.0.0", "-p", "10000"]