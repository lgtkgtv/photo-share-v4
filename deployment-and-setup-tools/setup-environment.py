#!/usr/bin/env python3
"""
Environment Setup Script for Photo Share Service
=================================================

This script helps set up a secure environment configuration for the photo sharing service.
"""

import os
import secrets
import string
import shutil
from pathlib import Path


def generate_secure_secret(length: int = 64) -> str:
    """Generate a cryptographically secure secret key."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_jwt_secret(length: int = 64) -> str:
    """Generate a secure JWT secret key."""
    # Use URL-safe characters for JWT
    alphabet = string.ascii_letters + string.digits + "-_"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def setup_environment(environment_type: str = "development"):
    """Set up environment configuration."""
    project_root = Path(__file__).parent.parent
    env_example_path = project_root / ".env.example"
    env_path = project_root / ".env"
    
    print(f"🔧 Setting up {environment_type} environment...")
    
    # Copy .env.example to .env if it doesn't exist
    if not env_path.exists():
        if env_example_path.exists():
            shutil.copy(env_example_path, env_path)
            print(f"✅ Copied .env.example to .env")
        else:
            print("❌ .env.example not found!")
            return False
    
    # Read current .env content
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Generate new secrets
    secret_key = generate_secure_secret()
    jwt_secret = generate_jwt_secret()
    grafana_password = generate_secure_secret(32)
    
    # Replace template values with secure ones
    replacements = {
        "your-very-secure-secret-key-here-change-in-production": secret_key,
        "generate_with_script_or_use_secure_random_string": jwt_secret,
        "change_this_password": grafana_password,
        "your_secure_password_here": generate_secure_secret(24)
    }
    
    for old_value, new_value in replacements.items():
        env_content = env_content.replace(old_value, new_value)
    
    # Update environment-specific settings
    if environment_type == "production":
        env_content = env_content.replace("ENVIRONMENT=development", "ENVIRONMENT=production")
        env_content = env_content.replace("LOG_LEVEL=INFO", "LOG_LEVEL=WARNING")
    elif environment_type == "test":
        env_content = env_content.replace("ENVIRONMENT=development", "ENVIRONMENT=test")
        env_content = env_content.replace("LOG_LEVEL=INFO", "LOG_LEVEL=DEBUG")
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Environment configuration updated!")
    print(f"🔐 Generated secure secrets for {environment_type}")
    print(f"📁 Configuration saved to: {env_path}")
    
    if environment_type == "production":
        print("\n⚠️  PRODUCTION SECURITY NOTES:")
        print("   1. Keep the .env file secure and never commit it to version control")
        print("   2. Use environment variables or secrets management in production")
        print("   3. Regularly rotate your JWT and secret keys")
        print("   4. Enable HTTPS/TLS for all external communications")
        print("   5. Review and update ALLOWED_ORIGINS for your frontend URLs")
    
    return True


def validate_environment():
    """Validate that environment is properly configured."""
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    required_vars = [
        "JWT_SECRET_KEY",
        "SECRET_KEY", 
        "POSTGRES_PASSWORD",
        "POSTGRES_USER",
        "POSTGRES_DB"
    ]
    
    missing_vars = []
    weak_secrets = []
    
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    for var in required_vars:
        if f"{var}=" not in env_content:
            missing_vars.append(var)
        else:
            # Extract value
            for line in env_content.split('\n'):
                if line.startswith(f"{var}="):
                    value = line.split('=', 1)[1]
                    # Check for template values that weren't replaced
                    if any(template in value for template in [
                        "your-very-secure",
                        "generate_with_script",
                        "change_this_password",
                        "your_secure_password_here"
                    ]):
                        weak_secrets.append(var)
                    break
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    if weak_secrets:
        print(f"⚠️  Weak/template secrets detected: {', '.join(weak_secrets)}")
        print("   Run setup_environment() to generate secure secrets")
        return False
    
    print("✅ Environment configuration is valid!")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up secure environment configuration")
    parser.add_argument(
        "--environment", 
        choices=["development", "production", "test"], 
        default="development",
        help="Environment type to configure"
    )
    parser.add_argument(
        "--validate-only", 
        action="store_true",
        help="Only validate existing configuration"
    )
    
    args = parser.parse_args()
    
    if args.validate_only:
        validate_environment()
    else:
        setup_environment(args.environment)
        print("\n🔍 Validating configuration...")
        validate_environment()