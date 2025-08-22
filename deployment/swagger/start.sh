#!/bin/sh
# Start Prism mock server
exec prism mock -h 0.0.0.0 -p 10000 --cors ./openapi.yaml