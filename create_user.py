#!/usr/bin/env python3
"""
Create User Script for SQLite and MySQL

This script creates a new superuser and saves to both SQLite and MySQL databases.
Usage: python create_user.py
"""

import os
import sys
from pathlib import Path

import django
import mysql.connector
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connections, transaction


# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


def get_env_var(key, default=""):
    """Get environment variable with default"""
    return os.environ.get(key, default)


def create_user_in_mysql(username, email, password):
    """Create user in MySQL database"""
    mysql_config = {
        "host": get_env_var("DB_HOST", "localhost"),
        "port": get_env_var("DB_PORT", "3306"),
        "user": get_env_var("DB_USER", "root"),
        "password": get_env_var("DB_PASSWORD", ""),
        "database": get_env_var("DB_NAME", "wagtail"),
        "charset": "utf8mb4",
        "collation": "utf8mb4_unicode_ci",
        "autocommit": True,
    }

    try:
        mysql_conn = mysql.connector.connect(**mysql_config)
        mysql_conn.cursor().execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")

        # Switch to the database
        db_name = get_env_var("DB_NAME", "wagtail")
        mysql_conn.database = db_name
        mysql_conn.cursor().execute(f"USE `{db_name}`")

        # Create user in auth_user table
        cursor = mysql_conn.cursor()
        cursor.execute(
            """
            INSERT INTO auth_user (username, email, password, is_staff, is_superuser, is_active, date_joined) 
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """,
            (username, email, "pbkdf2_sha256$" + password + "$", True, True, True),
        )

        mysql_conn.commit()
        print(f"✅ User '{username}' created in MySQL database")
        return True

    except Exception as e:
        print(f"❌ Error creating user in MySQL: {e}")
        return False


def create_user_in_django(username, email, password):
    """Create user using Django ORM (saves to SQLite)"""
    try:
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"⚠️ User '{username}' already exists in SQLite")
            return False

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

        print(f"✅ User '{username}' created in SQLite database")
        return True

    except Exception as e:
        print(f"❌ Error creating user in Django: {e}")
        return False


def get_user_input():
    """Get user details from command line"""
    print("Create New Superuser")
    print("=" * 30)

    username = input("Username: ").strip()
    if not username:
        print("❌ Username cannot be empty")
        return None, None, None

    email = input("Email: ").strip()
    if not email:
        print("❌ Email cannot be empty")
        return None, None, None

    password = input("Password: ").strip()
    if not password:
        print("❌ Password cannot be empty")
        return None, None, None

    confirm_password = input("Confirm Password: ").strip()
    if password != confirm_password:
        print("❌ Passwords do not match")
        return None, None, None

    return username, email, password


def main():
    """Main function"""
    print("User Creation for SQLite and MySQL")
    print("=" * 40)

    # Load environment variables
    load_env_file()

    # Ensure Django settings are configured
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "personal_portfolio.settings")

    try:
        django.setup()

        # Get user input
        user_data = get_user_input()
        if not user_data[0]:
            return

        username, email, password = user_data

        print(f"\nCreating user: {username}")
        print(f"Email: {email}")

        # Create user in SQLite (Django ORM)
        sqlite_success = create_user_in_django(username, email, password)

        # Create user in MySQL (direct connection)
        mysql_success = create_user_in_mysql(username, email, password)

        print("\n" + "=" * 40)
        if sqlite_success and mysql_success:
            print("✅ User created successfully in both databases!")
            print("\nNext steps:")
            print("1. Test login with the new user")
            print("2. Update DATABASE_URL in .env to use MySQL for production")
        elif sqlite_success:
            print("✅ User created in SQLite only")
            print("⚠️ MySQL creation failed - check MySQL connection")
        elif mysql_success:
            print("✅ User created in MySQL only")
            print("⚠️ SQLite creation failed - check Django configuration")
        else:
            print("❌ User creation failed in both databases")

    except Exception as e:
        print(f"❌ Setup error: {e}")


if __name__ == "__main__":
    main()
