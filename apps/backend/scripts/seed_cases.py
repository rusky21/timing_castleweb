import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.infrastructure.db.models import Case, Tag
from app.domain.entities import CaseCategory


async def seed_data():
    data_path = BASE_DIR / "data" / "cases.json"
    if not data_path.exists():
        print(f"❌ Error: {data_path} not found!")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        cases_data = json.load(f)

    # Initialize tables if not already created
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print(f"🌱 Starting seeding {len(cases_data)} cases...")

        for item in cases_data:
            # 1. Process tags
            tag_objects = []
            for tag_name in item.get("tags", []):
                tag_slug = tag_name.lower().replace(" ", "-").replace(".", "")
                result = await session.execute(select(Tag).where(Tag.name == tag_name))
                tag = result.scalar_one_or_none()
                if not tag:
                    tag = Tag(name=tag_name, slug=tag_slug)
                    session.add(tag)
                    await session.flush()
                tag_objects.append(tag)

            # 2. Check if case already exists by slug
            result = await session.execute(select(Case).where(Case.slug == item["slug"]))
            existing_case = result.scalar_one_or_none()

            category_enum = CaseCategory(item["category"])

            if existing_case:
                print(f"🔄 Updating existing case: {item['title']}")
                existing_case.title = item["title"]
                existing_case.client_name = item["client_name"]
                existing_case.year = item["year"]
                existing_case.category = category_enum
                existing_case.short_description = item["short_description"]
                existing_case.problem = item["problem"]
                existing_case.solution_fe = item["solution_fe"]
                existing_case.solution_be = item["solution_be"]
                existing_case.results_summary = item["results_summary"]
                existing_case.metrics = item.get("metrics", {})
                existing_case.live_url = item.get("live_url")
                existing_case.cover_image = item.get("cover_image")
                existing_case.gallery_images = item.get("gallery_images", [])
                existing_case.client_review = item.get("client_review")
                existing_case.client_author = item.get("client_author")
                existing_case.sort_order = item.get("sort_order", 0)
                existing_case.is_featured = item.get("is_featured", False)
                existing_case.tags = tag_objects
            else:
                print(f"➕ Creating new case: {item['title']}")
                new_case = Case(
                    slug=item["slug"],
                    title=item["title"],
                    client_name=item["client_name"],
                    year=item["year"],
                    category=category_enum,
                    short_description=item["short_description"],
                    problem=item["problem"],
                    solution_fe=item["solution_fe"],
                    solution_be=item["solution_be"],
                    results_summary=item["results_summary"],
                    metrics=item.get("metrics", {}),
                    live_url=item.get("live_url"),
                    cover_image=item.get("cover_image"),
                    gallery_images=item.get("gallery_images", []),
                    client_review=item.get("client_review"),
                    client_author=item.get("client_author"),
                    sort_order=item.get("sort_order", 0),
                    is_featured=item.get("is_featured", False),
                    tags=tag_objects
                )
                session.add(new_case)

        await session.commit()
        print("✅ Database successfully seeded with portfolio cases!")


if __name__ == "__main__":
    asyncio.run(seed_data())
