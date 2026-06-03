"""
Cache Administration Utility — MyFutureAbroad
Run from the project root with: .venv/Scripts/python scratch/cache_admin.py [command]

Commands:
  list            List all cache entries with their status
  clear <key>     Delete a specific cache entry (supports wildcards, e.g. %spain%)
  purge-bad       Auto-detect and delete entries containing Portugal mock data
  clear-all       Wipe the entire cache (nuclear option)
"""

import asyncio
import sys
import json
from datetime import datetime, timezone
from app.database import async_session
from app.models.cache import ContentCache
from sqlalchemy import select, delete

async def list_cache():
    async with async_session() as session:
        result = await session.execute(select(ContentCache).order_by(ContentCache.cache_key))
        rows = result.scalars().all()
        now = datetime.now(timezone.utc)
        print(f"\n{'KEY':<45} {'STATUS':<10} {'EXPIRES'}")
        print("-" * 80)
        for row in rows:
            expired = row.expires_at < now
            status = "EXPIRED" if expired else "VALID"
            # Flag likely mock/bad data
            preview = row.content_json.lower()[:300]
            if 'portugal' in preview and 'portugal' not in row.cache_key:
                status = "BAD-MOCK"
            print(f"{row.cache_key:<45} {status:<10} {row.expires_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"\nTotal: {len(rows)} entries")

async def clear_key(pattern):
    async with async_session() as session:
        result = await session.execute(
            select(ContentCache).where(ContentCache.cache_key.like(pattern))
        )
        rows = result.scalars().all()
        if not rows:
            print(f"No cache entries matching: {pattern}")
            return
        for row in rows:
            print(f"  Deleting: {row.cache_key}")
        await session.execute(
            delete(ContentCache).where(ContentCache.cache_key.like(pattern))
        )
        await session.commit()
        print(f"Deleted {len(rows)} entries.")

async def purge_bad():
    async with async_session() as session:
        result = await session.execute(select(ContentCache))
        rows = result.scalars().all()
        to_delete = [
            r.cache_key for r in rows
            if 'portugal' in r.content_json.lower()[:300] and 'portugal' not in r.cache_key
        ]
        if not to_delete:
            print("No bad mock entries found. Cache looks clean.")
            return
        print(f"Found {len(to_delete)} bad entries:")
        for k in to_delete:
            print(f"  - {k}")
        await session.execute(
            delete(ContentCache).where(ContentCache.cache_key.in_(to_delete))
        )
        await session.commit()
        print("Purged all bad mock entries.")

async def clear_all():
    confirm = input("This will wipe ALL cache entries. Type YES to confirm: ")
    if confirm.strip() != "YES":
        print("Aborted.")
        return
    async with async_session() as session:
        result = await session.execute(select(ContentCache))
        count = len(result.scalars().all())
        await session.execute(delete(ContentCache))
        await session.commit()
        print(f"Cleared {count} cache entries.")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "list":
        asyncio.run(list_cache())
    elif cmd == "clear" and len(sys.argv) > 2:
        asyncio.run(clear_key(sys.argv[2]))
    elif cmd == "purge-bad":
        asyncio.run(purge_bad())
    elif cmd == "clear-all":
        asyncio.run(clear_all())
    else:
        print(__doc__)
