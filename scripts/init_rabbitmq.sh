#!/usr/bin/env bash
set -e

echo "Waiting for RabbitMQ to be ready..."
# Wait until rabbitmqctl can successfully query status
until rabbitmqctl status > /dev/null 2>&1; do
  sleep 5
done

echo "Enabling all stable feature flags..."
# Enable every flag marked as 'stable'
rabbitmqctl list_feature_flags | awk '$2 == "stable" {print $1}' | xargs -r -n1 rabbitmqctl enable_feature_flag

echo "Restarting RabbitMQ application to apply feature flags..."
rabbitmqctl stop_app
rabbitmqctl start_app

echo "All stable feature flags enabled."
