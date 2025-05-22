#!/bin/sh

# Function to wait for RabbitMQ to be ready
wait_for_rabbitmq() {
  local retries=10
  while [ $retries -gt 0 ]; do
    if rabbitmqctl status > /dev/null 2>&1; then
      return 0
    fi
    echo "Waiting for RabbitMQ to start..."
    sleep 10
    retries=$((retries - 1))
  done
  return 1
}

# Ensure RabbitMQ storage directory permissions
echo "Ensuring RabbitMQ storage directory permissions as root..."
chown -R rabbitmq:rabbitmq /var/lib/rabbitmq
chmod -R 700 /var/lib/rabbitmq

# Fix permissions on .erlang.cookie explicitly
if [ ! -f /var/lib/rabbitmq/.erlang.cookie ]; then
  echo "Creating .erlang.cookie file..."
  echo "SOME_SECRET_COOKIE" > /var/lib/rabbitmq/.erlang.cookie
fi
chmod 400 /var/lib/rabbitmq/.erlang.cookie
chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie

# Ensure the mounted /data directory is used for RabbitMQ data
echo "Setting up RabbitMQ to use /var/lib/rabbitmq/mnesia for data storage..."
export RABBITMQ_MNESIA_DIR=/var/lib/rabbitmq/mnesia
export RABBITMQ_LOG_DIR=/var/lib/rabbitmq/log

# Create the data directory if it doesn't exist
if [ -d /var/lib/rabbitmq/mnesia ]; then
  echo "Data directory /var/lib/rabbitmq/mnesia exists."
else
  echo "Creating /var/lib/rabbitmq/mnesia..."
  mkdir -p /var/lib/rabbitmq/mnesia
  chown -R rabbitmq:rabbitmq /var/lib/rabbitmq/mnesia
fi

# Enable RabbitMQ management plugin
echo "Enabling RabbitMQ management plugin..."
rabbitmq-plugins enable rabbitmq_management

# Start RabbitMQ server in the background as rabbitmq user
echo "Starting RabbitMQ server in the background as rabbitmq user..."
rabbitmq-server -detached

echo "Waiting for RabbitMQ to start..."
sleep 10

# Check if RabbitMQ is ready
rabbitmqctl await_startup

# Check if user exists
if rabbitmqctl list_users | grep -q "fugu"; then
  echo "User 'fugu' already exists."
else
  echo "Creating RabbitMQ admin user as rabbitmq user..."
  rabbitmqctl add_user fugu fugu
  echo "Setting user tags as rabbitmq user..."
  rabbitmqctl set_user_tags fugu administrator
fi

# Create the vhost if it doesn't exist
if rabbitmqctl list_vhosts | grep -q "${RABBITMQ_VHOST}"; then
  echo "Vhost '${RABBITMQ_VHOST}' already exists."
else
  echo "Creating vhost '${RABBITMQ_VHOST}' for applications as rabbitmq user..."
  rabbitmqctl add_vhost ${RABBITMQ_VHOST}
fi

echo "Setting permissions as rabbitmq user..."
rabbitmqctl set_permissions -p ${RABBITMQ_VHOST} fugu ".*" ".*" ".*"

echo "Deleting default guest user as rabbitmq user..."
rabbitmqctl delete_user guest

echo "Stopping RabbitMQ server as rabbitmq user..."
rabbitmqctl stop

echo "Starting RabbitMQ server in foreground as rabbitmq user..."
exec rabbitmq-server
