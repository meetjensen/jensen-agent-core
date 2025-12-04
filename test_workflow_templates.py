#!/usr/bin/env python3
"""
Test script for F4-B: Global Workflow Template Catalog.

This script tests:
1. Creating workflow templates
2. Creating versions with major/minor versioning
3. Listing templates and versions
4. Publishing versions
5. Updating templates
6. Deleting templates
7. Version constraints and edge cases
"""
from __future__ import annotations

import sys
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app._db import DB_URL
from app.models.core_entities import Tenant, WorkflowTemplate, WorkflowTemplateVersion
from app.services.workflow_templates import (
    create_workflow_template,
    create_workflow_template_version,
    get_workflow_template_by_id,
    get_workflow_template_by_name,
    list_workflow_templates,
    get_workflow_template_version,
    get_latest_version,
    list_workflow_template_versions,
    publish_workflow_template_version,
    update_workflow_template,
    delete_workflow_template,
    create_next_minor_version,
    create_next_major_version,
)


def test_workflow_template_catalog():
    """Test the workflow template catalog functionality."""
    print("=" * 80)
    print("F4-B: Global Workflow Template Catalog Test")
    print("=" * 80)
    print()

    if not DB_URL:
        print("ERROR: DATABASE_URL (DB_URL) is not set")
        return False

    # Create engine and session
    engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()

    try:
        # Step 1: Get or create tenant
        print("Step 1: Getting or creating tenant...")
        tenant = session.query(Tenant).filter(Tenant.name == "Jensen").first()
        if tenant is None:
            tenant = Tenant(name="Jensen", type="internal", status="active")
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            print(f"  ✓ Created tenant: {tenant.id}")
        else:
            print(f"  ✓ Found existing tenant: {tenant.id}")
        print()

        # Step 2: Create workflow template
        print("Step 2: Creating workflow template...")
        template = create_workflow_template(
            session,
            tenant_id=tenant.id,
            name="Data Pipeline Automation",
            category="automation",
            description="Automated data pipeline for ETL operations",
            tags=["etl", "data", "automation"],
            status="draft",
        )
        print(f"  ✓ Created template: {template.id}")
        print(f"     Name: {template.name}")
        print(f"     Category: {template.category}")
        print(f"     Status: {template.status}")
        print(f"     Tags: {template.tags}")
        print()

        # Step 3: Create first version (1.0)
        print("Step 3: Creating version 1.0...")
        workflow_def_v1_0 = {
            "id": "data-pipeline-v1",
            "name": "Data Pipeline v1.0",
            "steps": [
                {"id": "extract", "type": "extract_data", "inputs": {"source": "db"}},
                {"id": "transform", "type": "transform_data", "inputs": {"rules": []}},
                {"id": "load", "type": "load_data", "inputs": {"target": "warehouse"}},
            ],
        }
        version_1_0 = create_workflow_template_version(
            session,
            template_id=template.id,
            version_major=1,
            version_minor=0,
            definition=workflow_def_v1_0,
            changelog="Initial version with basic ETL pipeline",
        )
        print(f"  ✓ Created version: {version_1_0.id}")
        print(f"     Version: {version_1_0.version_major}.{version_1_0.version_minor}")
        print(f"     Status: {version_1_0.status}")
        print(f"     Changelog: {version_1_0.changelog}")
        print()

        # Step 4: Create minor version using helper (1.1)
        print("Step 4: Creating version 1.1 using helper...")
        workflow_def_v1_1 = {
            "id": "data-pipeline-v1-1",
            "name": "Data Pipeline v1.1",
            "steps": [
                {"id": "extract", "type": "extract_data", "inputs": {"source": "db"}},
                {"id": "validate", "type": "validate_data", "inputs": {"schema": "v1"}},
                {"id": "transform", "type": "transform_data", "inputs": {"rules": []}},
                {"id": "load", "type": "load_data", "inputs": {"target": "warehouse"}},
            ],
        }
        version_1_1 = create_next_minor_version(
            session,
            template_id=template.id,
            definition=workflow_def_v1_1,
            changelog="Added data validation step",
        )
        print(f"  ✓ Created version: {version_1_1.id}")
        print(f"     Version: {version_1_1.version_major}.{version_1_1.version_minor}")
        print(f"     Changelog: {version_1_1.changelog}")
        print()

        # Step 5: Create major version using helper (2.0)
        print("Step 5: Creating version 2.0 using helper...")
        workflow_def_v2_0 = {
            "id": "data-pipeline-v2",
            "name": "Data Pipeline v2.0",
            "steps": [
                {"id": "extract", "type": "extract_data_parallel", "inputs": {"sources": ["db1", "db2"]}},
                {"id": "validate", "type": "validate_data", "inputs": {"schema": "v2"}},
                {"id": "transform", "type": "transform_data_parallel", "inputs": {"rules": []}},
                {"id": "load", "type": "load_data_batch", "inputs": {"target": "warehouse"}},
                {"id": "notify", "type": "send_notification", "inputs": {"channel": "slack"}},
            ],
        }
        version_2_0 = create_next_major_version(
            session,
            template_id=template.id,
            definition=workflow_def_v2_0,
            changelog="Major rewrite with parallel processing and notifications",
        )
        print(f"  ✓ Created version: {version_2_0.id}")
        print(f"     Version: {version_2_0.version_major}.{version_2_0.version_minor}")
        print(f"     Changelog: {version_2_0.changelog}")
        print()

        # Step 6: Test getting template by name
        print("Step 6: Testing get_workflow_template_by_name...")
        found_template = get_workflow_template_by_name(
            session,
            tenant_id=tenant.id,
            name="Data Pipeline Automation",
        )
        if found_template is None or found_template.id != template.id:
            print("  ✗ ERROR: Failed to find template by name")
            return False
        print(f"  ✓ Found template by name: {found_template.id}")
        print()

        # Step 7: Test listing all versions
        print("Step 7: Listing all versions of the template...")
        versions = list_workflow_template_versions(
            session,
            template_id=template.id,
        )
        print(f"  ✓ Found {len(versions)} versions:")
        for v in versions:
            print(f"     - v{v.version_major}.{v.version_minor}: {v.changelog}")
        if len(versions) != 3:
            print(f"  ✗ ERROR: Expected 3 versions, found {len(versions)}")
            return False
        print()

        # Step 8: Test get_latest_version
        print("Step 8: Getting latest version...")
        latest = get_latest_version(session, template_id=template.id)
        if latest is None:
            print("  ✗ ERROR: Failed to get latest version")
            return False
        print(f"  ✓ Latest version: {latest.version_major}.{latest.version_minor}")
        if latest.version_major != 2 or latest.version_minor != 0:
            print(f"  ✗ ERROR: Expected v2.0, got v{latest.version_major}.{latest.version_minor}")
            return False
        print()

        # Step 9: Test getting specific version
        print("Step 9: Getting specific version 1.1...")
        specific_version = get_workflow_template_version(
            session,
            template_id=template.id,
            version_major=1,
            version_minor=1,
        )
        if specific_version is None or specific_version.id != version_1_1.id:
            print("  ✗ ERROR: Failed to get specific version")
            return False
        print(f"  ✓ Found version 1.1: {specific_version.id}")
        print()

        # Step 10: Test publishing a version
        print("Step 10: Publishing version 2.0...")
        published_version, updated_template = publish_workflow_template_version(
            session,
            template_id=template.id,
            version_major=2,
            version_minor=0,
        )
        print(f"  ✓ Published version 2.0")
        print(f"     Version status: {published_version.status}")
        print(f"     Template status: {updated_template.status}")
        print(f"     Published at: {published_version.published_at}")
        if published_version.status != "published" or updated_template.status != "published":
            print("  ✗ ERROR: Status not updated to 'published'")
            return False
        print()

        # Step 11: Test get_latest_version with status filter
        print("Step 11: Getting latest published version...")
        latest_published = get_latest_version(
            session,
            template_id=template.id,
            status="published",
        )
        if latest_published is None or latest_published.id != version_2_0.id:
            print("  ✗ ERROR: Failed to get latest published version")
            return False
        print(f"  ✓ Latest published version: {latest_published.version_major}.{latest_published.version_minor}")
        print()

        # Step 12: Create second template
        print("Step 12: Creating second template...")
        template2 = create_workflow_template(
            session,
            tenant_id=tenant.id,
            name="Infrastructure Deployment",
            category="deployment",
            description="Automated infrastructure deployment workflow",
            tags=["infrastructure", "deployment", "terraform"],
            status="published",
        )
        print(f"  ✓ Created template: {template2.id}")
        print(f"     Name: {template2.name}")
        print()

        # Step 13: Test listing templates
        print("Step 13: Listing all templates...")
        all_templates = list_workflow_templates(
            session,
            tenant_id=tenant.id,
        )
        print(f"  ✓ Found {len(all_templates)} templates:")
        for t in all_templates:
            print(f"     - {t.name} ({t.category}) - {t.status}")
        if len(all_templates) < 2:
            print(f"  ✗ ERROR: Expected at least 2 templates, found {len(all_templates)}")
            return False
        print()

        # Step 14: Test listing templates with category filter
        print("Step 14: Listing templates by category 'automation'...")
        automation_templates = list_workflow_templates(
            session,
            tenant_id=tenant.id,
            category="automation",
        )
        print(f"  ✓ Found {len(automation_templates)} automation templates")
        if len(automation_templates) != 1:
            print(f"  ✗ ERROR: Expected 1 automation template, found {len(automation_templates)}")
            return False
        print()

        # Step 15: Test updating template
        print("Step 15: Updating template description...")
        updated_template = update_workflow_template(
            session,
            template_id=template.id,
            description="Enhanced automated data pipeline for ETL operations with validation",
            tags=["etl", "data", "automation", "validation"],
        )
        print(f"  ✓ Updated template")
        print(f"     New description: {updated_template.description}")
        print(f"     New tags: {updated_template.tags}")
        print()

        # Step 16: Test duplicate version constraint
        print("Step 16: Testing duplicate version constraint...")
        try:
            create_workflow_template_version(
                session,
                template_id=template.id,
                version_major=2,
                version_minor=0,
                definition={"test": "duplicate"},
                changelog="This should fail",
            )
            print("  ✗ ERROR: Duplicate version creation should have failed")
            return False
        except ValueError as e:
            print(f"  ✓ Duplicate version correctly rejected: {e}")
        print()

        # Step 17: Test version ordering
        print("Step 17: Testing version ordering...")
        ordered_versions = list_workflow_template_versions(
            session,
            template_id=template.id,
        )
        print(f"  ✓ Versions in order:")
        for v in ordered_versions:
            print(f"     - v{v.version_major}.{v.version_minor}")

        # Verify descending order
        for i in range(len(ordered_versions) - 1):
            curr = ordered_versions[i]
            next_v = ordered_versions[i + 1]
            if (curr.version_major < next_v.version_major or
                (curr.version_major == next_v.version_major and curr.version_minor < next_v.version_minor)):
                print("  ✗ ERROR: Versions not in descending order")
                return False
        print()

        # Step 18: Test deleting template (using template2)
        print("Step 18: Testing template deletion...")
        deleted = delete_workflow_template(session, template2.id)
        if not deleted:
            print("  ✗ ERROR: Failed to delete template")
            return False

        # Verify template is gone
        found = get_workflow_template_by_id(session, template2.id)
        if found is not None:
            print("  ✗ ERROR: Template still exists after deletion")
            return False
        print(f"  ✓ Successfully deleted template {template2.id}")
        print()

        # Step 19: Verify relationships
        print("Step 19: Verifying relationships...")
        session.refresh(template)
        print(f"  ✓ Template has {len(template.versions)} versions")
        if len(template.versions) != 3:
            print(f"  ✗ ERROR: Expected 3 versions, found {len(template.versions)}")
            return False

        for v in template.versions:
            if v.template_id != template.id:
                print(f"  ✗ ERROR: Version template_id mismatch")
                return False
        print(f"  ✓ All versions correctly linked to template")
        print()

        # Final summary
        print("=" * 80)
        print("Test Summary:")
        print("  ✓ Template creation")
        print("  ✓ Version creation (manual and helpers)")
        print("  ✓ Template retrieval (by ID and name)")
        print("  ✓ Version retrieval (specific and latest)")
        print("  ✓ Template and version listing")
        print("  ✓ Template and version filtering")
        print("  ✓ Version publishing")
        print("  ✓ Template updating")
        print("  ✓ Template deletion")
        print("  ✓ Duplicate version constraint")
        print("  ✓ Version ordering")
        print("  ✓ Relationship integrity")
        print("=" * 80)
        print("✓ F4-B: Global Workflow Template Catalog test PASSED!")
        print("=" * 80)
        return True

    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ F4-B test FAILED with error:")
        print(f"  {type(e).__name__}: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False

    finally:
        session.close()


if __name__ == "__main__":
    success = test_workflow_template_catalog()
    sys.exit(0 if success else 1)
