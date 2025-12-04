#!/usr/bin/env python3
"""
Initialize database tables for workflow template catalog.

This script creates the workflow_templates and workflow_template_versions
tables in the database.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from app._db import DB_URL
from app.models.core_entities import Base

def init_workflow_template_tables():
    """Create workflow template tables in the database."""
    if not DB_URL:
        print("ERROR: DATABASE_URL (DB_URL) is not set")
        return False

    print("Initializing workflow template tables...")
    print(f"Database URL: {DB_URL[:20]}...")

    engine = create_engine(DB_URL, pool_pre_ping=True, future=True)

    try:
        # Create all tables defined in Base
        Base.metadata.create_all(engine)
        print("✓ Successfully created workflow template tables")
        return True
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = init_workflow_template_tables()
    sys.exit(0 if success else 1)
