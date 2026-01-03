#!/usr/bin/env python3
"""
Example usage of SQLite to NeonDB migration script

This script demonstrates how to use the migration tool for your Wagtail project.
"""

import os
import subprocess
import sys

def load_env_file():
    """Load environment variables from .env file"""
    env_file = ".env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def run_migration():
    """Run the SQLite to NeonDB migration"""
    
    # Load environment variables from .env file
    load_env_file()
    
    # Configuration
    sqlite_path = "db.sqlite3"
    neon_url = os.getenv("DATABASE_URL")
    
    if not neon_url:
        print("Error: DATABASE_URL not found in .env file")
        print("Please add DATABASE_URL to your .env file:")
        print("DATABASE_URL=postgresql://user:password@host:port/database")
        sys.exit(1)
    
    if not os.path.exists(sqlite_path):
        print(f"Error: SQLite database '{sqlite_path}' not found")
        sys.exit(1)
    
    print("Starting SQLite to NeonDB migration...")
    print(f"SQLite database: {sqlite_path}")
    print(f"NeonDB URL: {neon_url.split('@')[1] if '@' in neon_url else 'hidden'}")
    
    # Install migration requirements
    print("\nInstalling migration requirements...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], 
                      check=True, capture_output=True, text=True)
        print("Migration requirements installed")
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        sys.exit(1)
    
    # Run migration
    print("\nRunning migration...")
    try:
        cmd = [
            sys.executable, 
            "migrate_sqlite_to_neon.py",
            "--sqlite-path", sqlite_path,
            "--neon-url", neon_url,
            "--verify"
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Migration completed successfully!")
        print("\nMigration output:")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Migration failed: {e}")
        print("Error output:")
        print(e.stderr)
        sys.exit(1)
    
    print("\nMigration completed successfully!")
    print("Please update your Django settings to use the NeonDB connection.")

def update_django_settings():
    """Update Django settings to use NeonDB"""
    
    settings_example = """
# Update your personal_portfolio/settings/base.py DATABASES configuration:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_neon_db_name',
        'USER': 'your_neon_user',
        'PASSWORD': 'your_neon_password',
        'HOST': 'your_neon_host',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Or using DATABASE_URL:
import dj_database_url
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
}
"""
    
    print(settings_example)

if __name__ == "__main__":
    print("SQLite to NeonDB Migration Tool")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("manage.py"):
        print("Error: Please run this script from your Django project root")
        sys.exit(1)
    
    # Run migration
    run_migration()
    
    # Show Django settings update instructions
    print("\nNext steps:")
    print("1. Update your Django settings to use NeonDB")
    update_django_settings()
    print("2. Test your application with the new database")
    print("3. Remove the old SQLite database file when confident")
