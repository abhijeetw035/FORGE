from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://forge_user:forge_pass@localhost:5432/forge")

def check_database():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version}")
            
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Existing tables: {tables}")
            
            if 'repositories' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM repositories"))
                count = result.fetchone()[0]
                logger.info(f"Repositories count: {count}")
            
            if 'commits' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM commits"))
                count = result.fetchone()[0]
                logger.info(f"Commits count: {count}")
            
            if 'functions' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM functions"))
                count = result.fetchone()[0]
                logger.info(f"Functions count: {count}")
            
            return True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False

if __name__ == "__main__":
    check_database()
