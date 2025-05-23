#!/bin/bash

# Start temporary HTTP-only NGINX config for Certbot bootstrap
nginx -c /code/config/nginx.conf -t && nginx -c /code/config/nginx.conf -s reload

# Run certbot to issue certificates and configure NGINX
# echo "[nginx-start.sh] Running certbot..."
# certbot --nginx --non-interactive --agree-tos \
# --email info@bragbooster.com \
# -d bragbooster.com -d www.bragbooster.com

# Stop temporary HTTP-only NGINX
nginx -c /code/config/nginx.conf -s stop
sleep 1

# Start cron for certificate renewal
service cron start

# Start Gunicorn app server
gunicorn backend.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8080 \
  --workers 1 \
  --timeout 90 \
  --log-level info &

# Start NGINX in the foreground with SSL
nginx -c /code/config/nginx.conf -g 'daemon off;'
