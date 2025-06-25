#!/usr/bin/env python3
"""Setup database and test connection."""
import asyncpg
import asyncio

async def setup_database():
    """Setup database with proper user."""
    try:
        # Try connecting with no specific user (default)
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            database='postgres'
        )
        
        # Check current users
        users = await conn.fetch("SELECT usename FROM pg_user")
        print("Current users:", [user['usename'] for user in users])
        
        # Check if privategpt user exists
        if 'privategpt' not in [user['usename'] for user in users]:
            print("Creating privategpt user...")
            await conn.execute("CREATE USER privategpt WITH PASSWORD 'secret';")
            print("✅ Created privategpt user")
        
        # Check if privategpt database exists
        databases = await conn.fetch("SELECT datname FROM pg_database")
        print("Current databases:", [db['datname'] for db in databases])
        
        if 'privategpt' not in [db['datname'] for db in databases]:
            print("Creating privategpt database...")
            await conn.execute("CREATE DATABASE privategpt OWNER privategpt;")
            await conn.execute("GRANT ALL PRIVILEGES ON DATABASE privategpt TO privategpt;")
            print("✅ Created privategpt database")
        
        await conn.close()
        
        # Test connection with privategpt user
        print("Testing connection with privategpt user...")
        conn2 = await asyncpg.connect(
            user='privategpt',
            password='secret',
            database='privategpt',
            host='localhost',
            port=5432
        )
        print("✅ Connected with privategpt user successfully!")
        await conn2.close()
        return True
        
    except Exception as e:
        print(f"Error with postgres user: {e}")
        
        # Try with privategpt user if it exists
        try:
            conn = await asyncpg.connect(
                user='privategpt',
                password='secret',
                database='privategpt',
                host='localhost',
                port=5432
            )
            print("Connected with privategpt user successfully!")
            await conn.close()
            return True
        except Exception as e2:
            print(f"Error with privategpt user: {e2}")
            return False

if __name__ == "__main__":
    asyncio.run(setup_database())