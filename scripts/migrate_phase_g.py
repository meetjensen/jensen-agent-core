#!/usr/bin/env python3
"""
Phase G Migration Script

Creates Phase G Template Catalog tables:
- workflow_templates
- workflow_template_versions

EXECUTION ORDER: Run FIRST (no dependencies)
IDEMPOTENT: Safe to run multiple times (uses checkfirst=True)

Usage:
    python scripts/migrate_phase_g.py

Or in Docker container:
    docker exec jensen-agent python scripts/migrate_phase_g.py

Dependencies:
    - PostgreSQL database with DATABASE_URL configured
    - No dependent tables required

Created tables:
    1. workflow_templates - Stores template metadata (key, name, owner, etc.)
    2. workflow_template_versions - Stores versioned workflow definitions

Related migrations:
    - migrate_phase_g1.py - Creates tenant/workspace/runs/tasks schema (independent)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect
from app._db import DB_URL
from app.models.core_entities import Base, WorkflowTemplate, WorkflowTemplateVersion


def migrate():
    """Create Phase G tables if they don't exist."""
    if not DB_URL:
        print("ERROR: DATABASE_URL is not set")
        sys.exit(1)

    print(f"Connecting to database...")
    engine = create_engine(DB_URL, pool_pre_ping=True, future=True)

    # Check which tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    print(f"Found {len(existing_tables)} existing tables")

    # Create only the Phase G tables
    tables_to_create = ["workflow_templates", "workflow_template_versions"]
    new_tables = [t for t in tables_to_create if t not in existing_tables]

    if not new_tables:
        print("✅ All Phase G tables already exist. No migration needed.")
        return

    print(f"Creating {len(new_tables)} new tables: {', '.join(new_tables)}")

    # Create only the new tables
    for table_name in new_tables:
        table = Base.metadata.tables[table_name]
        table.create(engine, checkfirst=True)
        print(f"  ✅ Created table: {table_name}")

    print("✅ Phase G migration complete!")


if __name__ == "__main__":
    migrate()
