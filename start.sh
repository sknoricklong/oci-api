#!/usr/bin/env bash

# use path of this example as working directory; enables starting this script from anywhere
cd "$(dirname "$0")"

# Load PORT from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# Default port if not set in .env
PORT=${port:-8000}

if [ "$1" = "prod" ]; then
    echo "Starting Uvicorn server in production mode..."

    # we also use a single worker in production mode so socket.io connections are always handled by the same worker
    uvicorn app.main:app --workers 1 --log-level info --port $PORT
elif [ "$1" = "dev" ]; then
    echo "Starting Uvicorn server in development mode..."

    # reload implies workers = 1
    uvicorn app.main:app --reload --log-level debug --port $PORT
else
    echo "Invalid parameter. Use 'prod' or 'dev'."
    exit 1
fi
