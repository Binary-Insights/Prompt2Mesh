#!/usr/bin/env python3
"""
User Instance Manager for Prompt2Mesh EKS Deployment

This script creates/deletes per-user Kubernetes instances by:
1. Generating manifests from templates
2. Applying them to the cluster via kubectl

Usage:
    python user_instance_manager.py create <user_id>
    python user_instance_manager.py delete <user_id>
    python user_instance_manager.py list
"""

import sys
import subprocess
import os
from pathlib import Path


def load_template(template_path: str) -> str:
    """Load the YAML template file."""
    with open(template_path, 'r') as f:
        return f.read()


def render_template(template: str, user_id: str) -> str:
    """Replace placeholders with actual user ID."""
    return template.replace('{{ USER_ID }}', user_id)


def apply_manifest(manifest: str):
    """Apply manifest to Kubernetes cluster."""
    result = subprocess.run(
        ['kubectl', 'apply', '-f', '-'],
        input=manifest.encode(),
        capture_output=True
    )
    if result.returncode != 0:
        print(f"Error applying manifest: {result.stderr.decode()}")
        sys.exit(1)
    print(result.stdout.decode())


def delete_manifest(manifest: str):
    """Delete manifest from Kubernetes cluster."""
    result = subprocess.run(
        ['kubectl', 'delete', '-f', '-'],
        input=manifest.encode(),
        capture_output=True
    )
    if result.returncode != 0:
        print(f"Error deleting manifest: {result.stderr.decode()}")
        sys.exit(1)
    print(result.stdout.decode())


def create_user_instance(user_id: str):
    """Create a new user instance."""
    print(f"Creating instance for user: {user_id}")
    
    # Load template
    template_path = Path(__file__).parent / 'per-user' / 'user-instance-template.yaml'
    template = load_template(template_path)
    
    # Render with user ID
    manifest = render_template(template, user_id)
    
    # Apply to cluster
    apply_manifest(manifest)
    
    print(f"Successfully created instance for user: {user_id}")
    print(f"Access URL: http://user-{user_id}.prompt2mesh.example.com")


def delete_user_instance(user_id: str):
    """Delete a user instance."""
    print(f"Deleting instance for user: {user_id}")
    
    # Load template
    template_path = Path(__file__).parent / 'per-user' / 'user-instance-template.yaml'
    template = load_template(template_path)
    
    # Render with user ID
    manifest = render_template(template, user_id)
    
    # Delete from cluster
    delete_manifest(manifest)
    
    print(f"Successfully deleted instance for user: {user_id}")


def list_user_instances():
    """List all user instances."""
    print("User instances in the cluster:")
    result = subprocess.run(
        ['kubectl', 'get', 'pods', '-n', 'prompt2mesh', '-l', 'app=blender', '-o', 'wide'],
        capture_output=True
    )
    print(result.stdout.decode())


def main():
    if len(sys.argv) < 2:
        print("Usage: python user_instance_manager.py {create|delete|list} [user_id]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'create':
        if len(sys.argv) < 3:
            print("Usage: python user_instance_manager.py create <user_id>")
            sys.exit(1)
        user_id = sys.argv[2]
        create_user_instance(user_id)
    
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("Usage: python user_instance_manager.py delete <user_id>")
            sys.exit(1)
        user_id = sys.argv[2]
        delete_user_instance(user_id)
    
    elif command == 'list':
        list_user_instances()
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python user_instance_manager.py {create|delete|list} [user_id]")
        sys.exit(1)


if __name__ == '__main__':
    main()
