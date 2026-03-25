#!/bin/bash
# Create .ssh directory
mkdir -p /root/.ssh

# Copy SSH keys from mount directory to standard directory
if [ -d "/mnt/.ssh" ]; then
    cp -r /mnt/.ssh/* /root/.ssh/
fi

# Set ownership and permissions (Required for SSH to run)
chown -R root:root /root/.ssh
chmod 700 /root/.ssh
chmod 600 /root/.ssh/*

# Run main command (Bot)
exec "$@"