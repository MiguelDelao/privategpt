"""
Base database configuration and session management
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from contextlib import contextmanager
import os
import logging
from typing import Generator

# Configure logging
logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

class DatabaseManager:
    """Centralized database management"""
    
    def __init__(self):
        """Initialize database manager with environment configuration"""
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://privategpt:secure_password_change_me@auth-postgres:5432/privategpt_auth"
        )
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    @contextmanager
    def get_session(self) -> Generator:
        """Get database session with proper cleanup
        
        Yields:
            Session: SQLAlchemy database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Database dependency for FastAPI
    
    Yields:
        Session: SQLAlchemy database session
    """
    with db_manager.get_session() as session:
        yield session 