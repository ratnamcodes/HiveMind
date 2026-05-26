"""Process-wide async MongoDB client built from the MDB_URI env var."""

from __future__ import annotations

import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None

DEFAULT_DB = "hivemind"


def get_mongo() -> AsyncIOMotorClient:
    """Return the shared async Motor client, lazy-initialized on first call."""
    global _client
    if _client is None:
        uri = os.getenv("MDB_URI")
        if not uri:
            raise RuntimeError(
                "MDB_URI is not set. Run `python scripts/provision_atlas.py` to provision Atlas."
            )
        _client = AsyncIOMotorClient(uri)
    return _client


def get_db(name: str = DEFAULT_DB) -> AsyncIOMotorDatabase:
    """Return the named database from the shared client."""
    return get_mongo()[name]


async def close_mongo() -> None:
    """Close the shared client. Safe to call when nothing was opened."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ping() -> None:
    """Ping the cluster and print 'pong' on success."""
    from dotenv import load_dotenv

    load_dotenv()
    result = await get_db().command("ping")
    if result.get("ok") != 1:
        raise RuntimeError(f"ping failed: {result}")
    print("pong")
    await close_mongo()
