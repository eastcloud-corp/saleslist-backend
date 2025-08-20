# Prism Mock Server用のDockerfile
FROM stoplight/prism:5

# 作業ディレクトリを設定
WORKDIR /app

# OpenAPI定義とサンプルデータをコピー
COPY openapi.yaml .
COPY examples ./examples

# ポート4010を公開
EXPOSE 4010

# Prismモックサーバーを起動（動的モード、CORS有効）
CMD ["mock", "-h", "0.0.0.0", "-p", "4010", "--cors", "-d", "openapi.yaml"]