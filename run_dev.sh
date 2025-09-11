#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Function to kill all background processes when the script exits
cleanup() {
    echo "Shutting down servers..."
    # The pkill command is used to kill all child processes of the current process
    pkill -P $$
}
trap cleanup EXIT

# --- Environment Variables ---
# Frontend variables (from vite.config.ts)
export LISTEN_PREFIX=${LISTEN_PREFIX:-}
export LISTEN_ADDRESS=${LISTEN_ADDRESS:-0.0.0.0}
export LISTEN_PORT=${LISTEN_PORT:-9080}
export BACKEND_PORT=${BACKEND_PORT:-8000}

# Backend variables (from api/config.py)
export STORAGE_PATH=${STORAGE_PATH:-./storage}
export API_PREFIX=${API_PREFIX:-/api}
export DATABASE_URL=${DATABASE_URL:-"postgresql+asyncpg://postgres:123321@localhost/socialsim"}


# --- Backend Setup ---
echo "Setting up and starting backend..."
# Create storage directory if it doesn't exist
mkdir -p $STORAGE_PATH
# Install dependencies
# pip install -r socialsimv4/api/requirements.txt
# Run database migrations/creations and seed the database
python -c "import asyncio; from socialsimv4.api.database import create_db_and_tables; asyncio.run(create_db_and_tables())"
python -m socialsimv4.api.seed
# Start server in the background
(uvicorn socialsimv4.api.server:app --host $LISTEN_ADDRESS --port $BACKEND_PORT --reload) &
BACKEND_PID=$!
echo "Backend server started with PID $BACKEND_PID on port $BACKEND_PORT"


# --- Frontend Setup ---
echo "Setting up and starting frontend..."
# Install dependencies and run dev server in the background
(cd socialsimv4/frontend && bun install && bun run dev) &
FRONTEND_PID=$!
echo "Frontend server started with PID $FRONTEND_PID on port $LISTEN_PORT"


# --- Wait for processes to finish ---
# The 'wait' command will wait for all background jobs to complete.
# Since the servers run indefinitely, this will keep the script alive.
# The cleanup trap will handle shutting them down on script exit (e.g., Ctrl+C).
echo "Development environment is running."
echo "Access frontend at http://$LISTEN_ADDRESS:$LISTEN_PORT"
echo "Press Ctrl+C to shut down."
wait
