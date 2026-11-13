import sys
import logging
from sqlalchemy import create_engine, text
from config import config
from database.models import Base, Website, User
from database.connection import get_engine, get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("webpulse.init_db")


def create_mysql_database_if_needed():
    """Ensure the target MySQL database exists before attempting table creation."""
    db_url = config.get_database_url()
    if not db_url.startswith("mysql"):
        return

    try:
        # Extract server URL without specific database
        base_url = f"mysql+pymysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}"
        server_engine = create_engine(base_url, future=True)
        with server_engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
                    f"DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;"
                )
            )
            conn.commit()
            logger.info(f"Verified/Created MySQL database '{config.DB_NAME}' successfully.")
    except Exception as e:
        logger.warning(
            f"Could not automatically create MySQL database '{config.DB_NAME}' from server root: {e}. "
            f"Will attempt direct connection to target DB."
        )


def seed_initial_data():
    """Populate initial production-grade demonstration websites if database is empty."""
    with get_db() as session:
        count = session.query(Website).count()
        if count == 0:
            logger.info("Database has no websites. Seeding standard production example websites...")
            examples = [
                Website(
                    name="Example Domain",
                    url="https://example.com",
                    monitoring_interval_seconds=60,
                    timeout_seconds=10,
                    is_active=True,
                    description="Standard IANA RFC 2606 example domain.",
                ),
                Website(
                    name="Python Official Portal",
                    url="https://www.python.org",
                    monitoring_interval_seconds=60,
                    timeout_seconds=10,
                    is_active=True,
                    description="Official website and download portal for Python language.",
                ),
                Website(
                    name="GitHub Status & Portal",
                    url="https://github.com",
                    monitoring_interval_seconds=60,
                    timeout_seconds=10,
                    is_active=True,
                    description="Global development and Git code hosting platform.",
                ),
            ]
            session.add_all(examples)
            session.commit()
            logger.info(f"Seeded {len(examples)} initial websites successfully.")
        else:
            logger.info(f"Database already contains {count} websites. Skipping seed.")


def init_database(seed: bool = True):
    """Create all schema tables and optionally seed default websites."""
    logger.info("Initializing database schema...")
    create_mysql_database_if_needed()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("All database tables created successfully.")
    if seed:
        seed_initial_data()
    logger.info("Database initialization completed.")


if __name__ == "__main__":
    try:
        init_database(seed=True)
        print("\n[OK] WebPulse database tables and seed data initialized successfully.")
    except Exception as err:
        print(f"\n[ERROR] Database initialization failed: {err}", file=sys.stderr)
        sys.exit(1)
