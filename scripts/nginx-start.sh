#!/bin/bash

# Start temporary HTTP-only NGINX config for Certbot bootstrap
nginx -t && nginx -s reload  # Ensure the config is valid before starting

# Run certbot to issue certificates and configure NGINX
# echo "[nginx-start.sh] Running certbot..."
# certbot --nginx --non-interactive --agree-tos \
# --email info@bragbooster.com \
# -d bragbooster.com -d www.bragbooster.com

# Stop temporary HTTP-only NGINX
killall nginx
sleep 1

# Start cron for certificate renewal
service cron start

# Start Gunicorn app server
gunicorn backend.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8880 \
  --workers 1 \
  --timeout 90 \
  --log-level info &

# Start NGINX in the foreground with SSL
nginx -g 'daemon off;'
