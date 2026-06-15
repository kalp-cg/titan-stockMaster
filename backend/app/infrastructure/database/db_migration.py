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
    async with engine.connect() as conn:
        logger.info("Starting database schema migration...")
        
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
        res = await conn.execute(text("SELECT id FROM users WHERE email = 'seed@titan.com'"))
        user = res.fetchone()
        if not user:
            # Hash 'seedpassword' as the default
            default_hashed = hash_password("seedpassword")
            await conn.execute(text("""
                INSERT INTO users (id, email, hashed_password, created_at)
                VALUES ('00000000-0000-0000-0000-000000000000', 'seed@titan.com', :hashed, NOW())
            """), {"hashed": default_hashed})
            logger.info("Seeded default user 'seed@titan.com'")

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
        # If we dropped ix_holdings_ticker, we want to make sure ticker is indexed.
        # But wait, it's already part of the composite unique index as the second column.
        # However, to be fully safe, let's make sure it's indexed. If 'ix_holdings_ticker' was dropped,
        # we can add it as a normal index if needed, or leave it since (user_id, ticker) covers it if user_id is queried.
        # Actually, adding a normal index on ticker is good.
        # Let's see if there's any index on ticker
        if 'ix_holdings_ticker' not in index_names and 'ix_holdings_ticker_non_unique' not in index_names:
            await conn.execute(text("ALTER TABLE holdings ADD INDEX ix_holdings_ticker_non_unique (ticker)"))

        logger.info("Database schema migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_migration())
