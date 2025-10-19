#!/bin/bash
set -euo pipefail

echo "🔄 Running database migrations..."
python manage.py migrate --noinput

if [[ "${ENABLE_SAMPLE_DATA:-False}" == "True" ]]; then
  echo "🌱 Seeding sample data..."
  python seed_data.py || echo "⚠️ Sample data seeding encountered an issue (continuing)"
fi

if [[ "${ENABLE_CACHE_TABLE:-True}" == "True" ]]; then
  echo "🗂️ Ensuring cache table exists..."
  python manage.py createcachetable || echo "⚠️ Cache table setup issue (continuing)"
fi

echo "🚀 Starting development server..."
exec python manage.py runserver 0.0.0.0:8000
