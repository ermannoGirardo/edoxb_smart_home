#!/bin/sh
# Script per aspettare che il backend sia disponibile prima di avviare nginx

set -e

host="$1"
port="$2"
shift 2

until nc -z "$host" "$port"; do
  >&2 echo "Backend $host:$port non disponibile - in attesa..."
  sleep 1
done

>&2 echo "Backend $host:$port è disponibile!"
exec "$@"

