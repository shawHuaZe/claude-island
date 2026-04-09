import aiosqlite
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel
from contextlib import asynccontextmanager
import os

DATABASE_URL = os.path.join(os.path.dirname(__file__), "..", "..", "data", "claude_island.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE_URL), exist_ok=True)


async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.exec_driver_sql("PRAGMA foreign_keys = ON")
        await db.commit()
    async with AsyncSession.create(engine=None) as session:
        async with session.begin():
            SQLModel.metadata.create_all(session.bind)


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        try:
            yield db
        finally:
            await db.close()
