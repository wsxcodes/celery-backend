#!/bin/sh

# List all feature flags and filter for stable ones
stable_flags=$(rabbitmqctl feature_flags list | awk '/^Name/ {getline; while ($1 != "") {print $1; getline}}')

# Enable each stable feature flag
for flag in $stable_flags; do
  echo "Enabling feature flag: $flag"
  rabbitmqctl feature_flags enable "$flag"
done
