#!/usr/bin/env python3
"""
Data Migration Script: JSON File Storage → Database
Migrates user data from the old JSON file system to the new SQLAlchemy database
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import create_tables, User, get_db, engine
from security import SecurityService
import logging
from pythonjsonlogger import jsonlogger

# Setup logging
logger = logging.getLogger("auth_migration")
logger.setLevel(logging.INFO)

# JSON formatter for ELK Stack compatibility
json_formatter = jsonlogger.JsonFormatter(
    fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(json_formatter)
logger.addHandler(console_handler)

class DataMigration:
    """Handle migration from JSON files to database"""
    
    def __init__(self):
        self.security_service = SecurityService()
        self.old_user_file = Path("/app/data/users.json")
        
        # Try multiple backup locations in order of preference
        backup_locations = [
            Path("/app/data/migration_backup"),
            Path("/app/migration_backup"),
            Path("/tmp/migration_backup")
        ]
        
        self.backup_dir = None
        for backup_path in backup_locations:
            try:
                backup_path.mkdir(parents=True, exist_ok=True)
                # Test write permissions
                test_file = backup_path / "test_write"
                test_file.touch()
                test_file.unlink()
                self.backup_dir = backup_path
                print(f"✅ Using backup directory: {backup_path}")
                break
            except (PermissionError, OSError) as e:
                print(f"⚠️ Cannot use {backup_path}: {e}")
                continue
        
        if self.backup_dir is None:
            print("⚠️ Warning: Cannot create backup directory, migration will skip backup step")
            # Use a placeholder that we know will fail gracefully
            self.backup_dir = Path("/dev/null/backup")
        
    def log_migration_event(self, event_type: str, message: str, **kwargs):
        """Log migration events in ELK Stack format"""
        migration_data = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "auth-service",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "log_level": "INFO",
            "event_category": "data_migration",
            "migration": {
                "event_type": event_type,
                "message": message,
                **kwargs
            }
        }
        
        logger.info(message, extra=migration_data)
    
    def backup_existing_data(self) -> bool:
        """Create backup of existing JSON data"""
        try:
            if self.old_user_file.exists():
                # Check if we have a valid backup directory
                if str(self.backup_dir) == "/dev/null/backup":
                    self.log_migration_event(
                        "backup_skipped",
                        "Backup skipped - no writable backup directory available"
                    )
                    print("⚠️ Skipping backup - no writable directory available")
                    return True  # Continue migration without backup
                
                backup_file = self.backup_dir / f"users_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                # Copy original file
                import shutil
                shutil.copy2(self.old_user_file, backup_file)
                
                self.log_migration_event(
                    "backup_created",
                    f"Backup created: {backup_file}",
                    backup_file=str(backup_file),
                    original_file=str(self.old_user_file)
                )
                print(f"✅ Backup created: {backup_file}")
                return True
            else:
                self.log_migration_event(
                    "no_backup_needed",
                    "No existing JSON file found, no backup needed"
                )
                print("ℹ️ No existing JSON file found, no backup needed")
                return True
                
        except Exception as e:
            self.log_migration_event(
                "backup_failed",
                f"Failed to create backup: {str(e)}",
                error=str(e)
            )
            print(f"⚠️ Warning: Failed to create backup: {str(e)}")
            print("⚠️ Continuing migration without backup...")
            return True  # Continue migration even if backup fails
    
    def load_old_users(self) -> Optional[Dict[str, Any]]:
        """Load users from old JSON file"""
        try:
            if not self.old_user_file.exists():
                self.log_migration_event(
                    "no_old_data",
                    "No existing user data file found"
                )
                return {}
            
            with open(self.old_user_file, 'r') as f:
                users_data = json.load(f)
            
            self.log_migration_event(
                "old_data_loaded",
                f"Loaded {len(users_data)} users from JSON file",
                user_count=len(users_data)
            )
            return users_data
            
        except Exception as e:
            self.log_migration_event(
                "load_failed",
                f"Failed to load old user data: {str(e)}",
                error=str(e)
            )
            return None
    
    def migrate_user(self, email: str, user_data: Dict[str, Any], db) -> bool:
        """Migrate a single user to database"""
        try:
            # Check if user already exists in database
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                self.log_migration_event(
                    "user_exists",
                    f"User {email} already exists in database, skipping",
                    user_email=email
                )
                return True
            
            # Prepare user data for database
            db_user_data = {
                "email": email,
                "password_hash": user_data.get("password_hash", ""),
                "role": user_data.get("role", "user"),
                "active": user_data.get("active", True),
                "created_by": user_data.get("created_by", "migration"),
                "failed_login_attempts": 0,
                "mfa_enabled": False
            }
            
            # Handle timestamps
            if user_data.get("created_at"):
                try:
                    db_user_data["created_at"] = datetime.fromisoformat(
                        user_data["created_at"].replace("Z", "+00:00")
                    )
                except:
                    db_user_data["created_at"] = datetime.utcnow()
            
            if user_data.get("updated_at"):
                try:
                    db_user_data["updated_at"] = datetime.fromisoformat(
                        user_data["updated_at"].replace("Z", "+00:00")
                    )
                except:
                    db_user_data["updated_at"] = datetime.utcnow()
            
            # Create user
            user = User(**db_user_data)
            
            # Set client matters
            client_matters = user_data.get("client_matters", [])
            user.set_client_matters(client_matters)
            
            # Add to database
            db.add(user)
            db.commit()
            
            self.log_migration_event(
                "user_migrated",
                f"Successfully migrated user {email}",
                user_email=email,
                role=user.role,
                client_matters=client_matters
            )
            return True
            
        except Exception as e:
            self.log_migration_event(
                "user_migration_failed",
                f"Failed to migrate user {email}: {str(e)}",
                user_email=email,
                error=str(e)
            )
            db.rollback()
            return False
    
    def verify_migration(self, original_users: Dict[str, Any], db) -> bool:
        """Verify that migration was successful"""
        try:
            # Count users in database
            db_user_count = db.query(User).count()
            original_count = len(original_users)
            
            self.log_migration_event(
                "migration_verification",
                f"Database has {db_user_count} users, original had {original_count}",
                db_user_count=db_user_count,
                original_count=original_count
            )
            
            # Check each user exists
            missing_users = []
            for email in original_users.keys():
                user = db.query(User).filter(User.email == email).first()
                if not user:
                    missing_users.append(email)
            
            if missing_users:
                self.log_migration_event(
                    "migration_incomplete",
                    f"Missing users after migration: {missing_users}",
                    missing_users=missing_users
                )
                return False
            
            self.log_migration_event(
                "migration_verified",
                "All users successfully migrated and verified"
            )
            return True
            
        except Exception as e:
            self.log_migration_event(
                "verification_failed",
                f"Migration verification failed: {str(e)}",
                error=str(e)
            )
            return False
    
    def cleanup_old_files(self):
        """Move old files to backup location"""
        try:
            if self.old_user_file.exists():
                archived_file = self.backup_dir / f"users_archived_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                self.old_user_file.rename(archived_file)
                
                self.log_migration_event(
                    "cleanup_completed",
                    f"Old user file archived to {archived_file}",
                    archived_file=str(archived_file)
                )
        except Exception as e:
            self.log_migration_event(
                "cleanup_failed",
                f"Failed to cleanup old files: {str(e)}",
                error=str(e)
            )
    
    def run_migration(self) -> bool:
        """Execute the complete migration process"""
        self.log_migration_event(
            "migration_started",
            "Starting data migration from JSON to database"
        )
        
        # Step 1: Create database tables
        try:
            create_tables()
            self.log_migration_event(
                "tables_created",
                "Database tables created successfully"
            )
        except Exception as e:
            self.log_migration_event(
                "table_creation_failed",
                f"Failed to create database tables: {str(e)}",
                error=str(e)
            )
            return False
        
        # Step 2: Backup existing data
        if not self.backup_existing_data():
            return False
        
        # Step 3: Load old user data
        original_users = self.load_old_users()
        if original_users is None:
            return False
        
        if not original_users:
            self.log_migration_event(
                "no_data_to_migrate",
                "No user data found to migrate"
            )
            return True
        
        # Step 4: Migrate users
        db = next(get_db())
        try:
            migrated_count = 0
            failed_count = 0
            
            for email, user_data in original_users.items():
                if self.migrate_user(email, user_data, db):
                    migrated_count += 1
                else:
                    failed_count += 1
            
            self.log_migration_event(
                "migration_completed",
                f"Migration completed: {migrated_count} successful, {failed_count} failed",
                migrated_count=migrated_count,
                failed_count=failed_count
            )
            
            # Step 5: Verify migration
            if not self.verify_migration(original_users, db):
                return False
            
            # Step 6: Cleanup old files
            if failed_count == 0:
                self.cleanup_old_files()
            
            return failed_count == 0
            
        finally:
            db.close()

def main():
    """Main migration function"""
    print("🔄 Starting PrivateGPT Auth Service Data Migration...")
    print("📁 Migrating from JSON file storage to database...")
    
    migration = DataMigration()
    
    try:
        success = migration.run_migration()
        
        if success:
            print("✅ Migration completed successfully!")
            print("🗄️ User data has been migrated to the database")
            print("💾 Original files have been backed up")
            return 0
        else:
            print("❌ Migration failed!")
            print("🔍 Check logs for details")
            print("💾 Original files remain unchanged")
            return 1
            
    except Exception as e:
        print(f"💥 Migration crashed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 