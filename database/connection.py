import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from config import config

logger = logging.getLogger("webpulse.database")

_engine = None
_SessionFactory = None


def get_engine():
    """Create or return the cached SQLAlchemy database engine with connection pooling."""
    global _engine
    if _engine is None:
        db_url = config.get_database_url()
        is_sqlite = db_url.startswith("sqlite")
        
        connect_args = {}
        engine_kwargs = {
            "future": True,
            "echo": False,
        }
        
        if is_sqlite:
            connect_args["check_same_thread"] = False
        else:
            # Production MySQL settings
            engine_kwargs.update({
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,  # Test connections before checkout
                "pool_recycle": 3600,   # Recycle connections after 1 hour
            })

        logger.info(f"Initializing SQLAlchemy Engine with: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        try:
            temp_engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
            # Verify connectivity
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _engine = temp_engine
        except Exception as conn_err:
            if not is_sqlite and (not config.DB_PASSWORD or "Access denied" in str(conn_err) or "Can't connect" in str(conn_err)):
                fallback_url = "sqlite:///webpulse.db"
                logger.warning(
                    f"MySQL connection failed ({conn_err}). "
                    f"Falling back to local SQLite database ({fallback_url}) so the application can run immediately. "
                    f"Configure DB_PASSWORD in .env to use MySQL 8.x."
                )
                _engine = create_engine(fallback_url, connect_args={"check_same_thread": False}, future=True)
            else:
                # Re-raise if sqlite failed or user specified explicit DATABASE_URL
                raise conn_err
    return _engine


def get_session_factory():
    """Return thread-safe scoped session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = scoped_session(sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine))
    return _SessionFactory


@contextmanager
def get_db():
    """
    Context manager for database sessions.
    Guarantees that transactions are committed upon success, rolled back on error,
    and sessions are safely closed.
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error: {str(e)}")
        raise
    finally:
        session.close()


def test_connection():
    """
    Validate database connectivity.
    Returns (True, message) on success, or (False, error_message) on failure.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection operational"
    except Exception as exc:
        return False, str(exc)
