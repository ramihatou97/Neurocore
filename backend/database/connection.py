"""
Database connection management with connection pooling
Provides database session management for the application
"""

from sqlalchemy import create_engine, event, exc, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging

from backend.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Database connection manager with connection pooling

    Features:
    - QueuePool with configurable pool size
    - Automatic connection health checks (pool_pre_ping)
    - Connection pool recycling to avoid stale connections
    - Session management with context managers
    - Connection health check endpoint support
    """

    def __init__(self):
        """Initialize database connection pool"""
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Create SQLAlchemy engine with connection pool"""
        try:
            # Create engine with QueuePool
            self.engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=settings.DB_POOL_SIZE,  # Number of persistent connections
                max_overflow=settings.DB_MAX_OVERFLOW,  # Additional connections allowed
                pool_timeout=settings.DB_POOL_TIMEOUT,  # Timeout for getting connection
                pool_recycle=settings.DB_POOL_RECYCLE,  # Recycle connections after 1 hour
                pool_pre_ping=True,  # Verify connections before using
                echo=settings.DEBUG,  # Log all SQL statements if DEBUG=True
                future=True  # Use SQLAlchemy 2.0 API
            )

            # Create sessionmaker
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )

            # Add event listeners
            self._add_event_listeners()

            logger.info(
                f"Database connection pool initialized: "
                f"pool_size={settings.DB_POOL_SIZE}, "
                f"max_overflow={settings.DB_MAX_OVERFLOW}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize database connection: {str(e)}")
            raise

    def _add_event_listeners(self):
        """Add event listeners for connection lifecycle"""

        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Called when a new database connection is created"""
            logger.debug("New database connection created")

        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Called when a connection is checked out from the pool"""
            logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Called when a connection is returned to the pool"""
            logger.debug("Connection returned to pool")

    def get_session(self) -> Session:
        """
        Get a new database session

        Returns:
            Session: SQLAlchemy session

        Usage:
            session = db.get_session()
            try:
                # Use session
                user = session.query(User).first()
                session.commit()
            finally:
                session.close()
        """
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations

        Yields:
            Session: SQLAlchemy session

        Usage:
            with db.session_scope() as session:
                user = session.query(User).first()
                # Automatically commits on success, rolls back on exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {str(e)}")
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """
        Check database connection health

        Returns:
            bool: True if database is accessible, False otherwise

        Usage:
            if db.health_check():
                print("Database is healthy")
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.debug("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    def get_pool_status(self) -> dict:
        """
        Get current connection pool status

        Returns:
            dict: Pool status information

        Usage:
            status = db.get_pool_status()
            print(f"Pool size: {status['pool_size']}, Checked out: {status['checked_out']}")
        """
        if self.engine is None:
            return {}

        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else None
        }

    def create_all_tables(self):
        """
        Create all tables defined in models

        Warning: Only use for development/testing. Use migrations for production.

        Usage:
            db.create_all_tables()
        """
        from backend.database.models import Base
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("All database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise

    def drop_all_tables(self):
        """
        Drop all tables

        Warning: This will delete all data! Only use for development/testing.

        Usage:
            db.drop_all_tables()
        """
        from backend.database.models import Base
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {str(e)}")
            raise

    def dispose(self):
        """
        Dispose of the connection pool

        Call this when shutting down the application

        Usage:
            db.dispose()
        """
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection pool disposed")


# Global database connection instance
db = DatabaseConnection()


# Dependency for FastAPI routes
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions

    Usage in FastAPI routes:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
