import asyncio
from sqlalchemy import text, inspect
from app.infrastructure.database.engine import get_engine
from app.utils.logging import get_logger
import hashlib
import os

logger = get_logger(__name__)

# Simple PBKDF2 password hashing matching our auth_service logic
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return salt.hex() + ":" + key.hex()

async def run_migration():
    engine = get_engine()
    dialect = engine.dialect.name
    from datetime import datetime

    if "mysql" not in dialect:
        logger.info(f"Dialect is '{dialect}'. Skipping raw MySQL ALTER migrations, running database-agnostic seed check...")
        async with engine.connect() as conn:
            try:
                res = await conn.execute(text("SELECT id FROM users WHERE email = 'seed@helixdecidex.com'"))
                user = res.fetchone()
                if not user:
                    default_hashed = hash_password("seedpassword")
                    await conn.execute(text("""
                        INSERT INTO users (id, email, hashed_password, created_at)
                        VALUES ('00000000-0000-0000-0000-000000000000', 'seed@helixdecidex.com', :hashed, :created_at)
                    """), {"hashed": default_hashed, "created_at": datetime.utcnow()})
                    await conn.execute(text("COMMIT")) # Wait, actually SQLAlchemy connection does not auto-commit raw DML unless we commit, but conn.commit() was there. Let's keep it.
                    await conn.commit()
                    logger.info("Seeded default user 'seed@helixdecidex.com' in database.")
            except Exception as e:
                logger.error("Failed to seed default user in database", error=str(e))
        return

    async with engine.connect() as conn:
        logger.info("Starting MySQL database schema migration...")
        
        # 1. Create users table if not exists
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL,
                UNIQUE KEY uq_users_email (email)
            ) ENGINE=InnoDB;
        """))
        logger.info("Table 'users' verified/created.")

        # 2. Seed default user if not exists
        res = await conn.execute(text("SELECT id FROM users WHERE email = 'seed@helixdecidex.com'"))
        user = res.fetchone()
        if not user:
            # Hash 'seedpassword' as the default
            default_hashed = hash_password("seedpassword")
            await conn.execute(text("""
                INSERT INTO users (id, email, hashed_password, created_at)
                VALUES ('00000000-0000-0000-0000-000000000000', 'seed@helixdecidex.com', :hashed, :created_at)
            """), {"hashed": default_hashed, "created_at": datetime.utcnow()})
            await conn.commit()
            logger.info("Seeded default user 'seed@helixdecidex.com'")

        # 3. Modify holdings table: inspect columns
        columns = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_columns("holdings"))
        col_names = [col['name'] for col in columns]
        
        if 'user_id' not in col_names:
            logger.info("Adding 'user_id' column to 'holdings' table...")
            await conn.execute(text("ALTER TABLE holdings ADD COLUMN user_id VARCHAR(36) NULL"))
            await conn.commit()

        # 4. Update existing records with default user_id if null
        await conn.execute(text("""
            UPDATE holdings 
            SET user_id = '00000000-0000-0000-0000-000000000000' 
            WHERE user_id IS NULL
        """))
        logger.info("Updated existing holdings with default user ID.")

        # 5. Make user_id NOT NULL
        await conn.execute(text("ALTER TABLE holdings MODIFY user_id VARCHAR(36) NOT NULL"))

        # 6. Drop old unique index on ticker (ix_holdings_ticker) if it exists
        indexes = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_indexes("holdings"))
        index_names = [idx['name'] for idx in indexes]
        
        if 'ix_holdings_ticker' in index_names:
            # Check if it is unique
            for idx in indexes:
                if idx['name'] == 'ix_holdings_ticker' and idx['unique']:
                    logger.info("Dropping unique index 'ix_holdings_ticker' from holdings...")
                    await conn.execute(text("ALTER TABLE holdings DROP INDEX ix_holdings_ticker"))
                    break

        # 7. Add composite unique constraint/index on (user_id, ticker) if not exists
        if 'ix_holdings_user_id_ticker' not in index_names:
            logger.info("Creating composite unique index 'ix_holdings_user_id_ticker' on holdings(user_id, ticker)...")
            await conn.execute(text("ALTER TABLE holdings ADD UNIQUE INDEX ix_holdings_user_id_ticker (user_id, ticker)"))

        # 8. Re-add a non-unique index on ticker for fast queries if not already present
        if 'ix_holdings_ticker' not in index_names and 'ix_holdings_ticker_non_unique' not in index_names:
            await conn.execute(text("ALTER TABLE holdings ADD INDEX ix_holdings_ticker_non_unique (ticker)"))

        logger.info("Database schema migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_migration())
