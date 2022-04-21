#!/bin/sh

# Pass the HOST_UID and HOST_UID from environment variables specified in the child image docker-compose
HOST_GID=${HOST_GID}
HOST_UID=${HOST_UID}

echo "Starting antibody-api container with the same host user UID: $HOST_UID and GID: $HOST_GID"

# Create a new user with the same host UID to run processes on container
# The Filesystem doesn't really care what the user is called,
# it only cares about the UID attached to that user
# Check if user already exists and don't recreate across container restarts
getent passwd $HOST_UID > /dev/null
# $? is a special variable that captures the exit status of last task
if [ $? -ne 0 ]; then
    addgroup -g $HOST_GID -S hubmap
    adduser -S -u $HOST_UID -g $HOST_GID hubmap
fi

# Lastly we use su-exec to execute our process "$@" as that user
# Remember CMD from a Dockerfile of child image gets passed to the entrypoint.sh as command line arguments
# "$@" is a shell variable that means "all the arguments"
exec /sbin/su-exec hubmap "$@"
