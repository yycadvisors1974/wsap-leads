"""
sync_status_to_supabase.py — Sync Follow-up Status & Remarks from Excel to Supabase.

Reads the master Excel, compares with Supabase, and updates rows where
Follow-up Status or Remarks have changed.

Usage:
    python sync_status_to_supabase.py
    python sync_status_to_supabase.py --dry-run

Set environment variable first:
    set SUPABASE_KEY=your_service_role_key_here
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from supabase import create_client

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://kpwsvitvsorloefoikkx.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

MASTER_EXCEL = r"C:\Users\ChooBeyNi\YYC Holdings Sdn Bhd\BD - WSAP\WSAP leads for all salesperson.xlsx"
SHEET_NAME = "Compiled"


def clean_str(val):
    """Normalize a value to a comparable string."""
    if val is None:
        return ""
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", ""):
        return ""
    return s


def main():
    parser = argparse.ArgumentParser(description="Sync calling status from Excel to Supabase.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without updating")
    args = parser.parse_args()

    if not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_KEY environment variable first.")
        print('  set SUPABASE_KEY=your_service_role_key_here')
        sys.exit(1)

    print("=" * 60)
    print("WSAP Leads — Sync Calling Status to Supabase")
    print("=" * 60)
    if args.dry_run:
        print("*** DRY RUN — no data will be updated ***\n")

    # Connect to Supabase
    print("Connecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Read Excel
    print(f"Reading Excel: {MASTER_EXCEL}")
    df_excel = pd.read_excel(MASTER_EXCEL, sheet_name=SHEET_NAME)
    print(f"  Excel rows: {len(df_excel)}")

    # Fetch all leads from Supabase
    print("Fetching current data from Supabase...")
    all_rows = []
    offset = 0
    while True:
        resp = supabase.table("leads").select("pk,id,company_name,followup_status,remarks").range(offset, offset + 999).execute()
        all_rows.extend(resp.data)
        if len(resp.data) < 1000:
            break
        offset += 1000
    print(f"  Supabase rows: {len(all_rows)}")

    # Build lookup: (id, company_name_lower) -> {pk, followup_status, remarks}
    db_lookup = {}
    for row in all_rows:
        key = (str(row["id"]).strip(), clean_str(row.get("company_name")).lower())
        db_lookup[key] = {
            "pk": row["pk"],
            "followup_status": clean_str(row.get("followup_status")),
            "remarks": clean_str(row.get("remarks")),
        }

    # Compare Excel vs Supabase
    changes = []
    not_found = 0

    for _, excel_row in df_excel.iterrows():
        raw_id = excel_row.get("ID", "")
        # Handle float IDs like 33865.0 → "33865"
        try:
            excel_id = str(int(float(raw_id)))
        except (ValueError, TypeError):
            excel_id = str(raw_id).strip()
        excel_company = clean_str(excel_row.get("Company Name")).lower()
        key = (excel_id, excel_company)

        db_row = db_lookup.get(key)
        if not db_row:
            not_found += 1
            continue

        excel_status = clean_str(excel_row.get("Follow-up Status"))
        excel_remarks = clean_str(excel_row.get("Remarks"))

        updates = {}
        if excel_status and excel_status != db_row["followup_status"]:
            updates["followup_status"] = excel_status
        if excel_remarks != db_row["remarks"]:
            updates["remarks"] = excel_remarks if excel_remarks else None

        if updates:
            changes.append({
                "pk": db_row["pk"],
                "id": excel_id,
                "company": excel_company,
                "updates": updates,
                "old_status": db_row["followup_status"],
                "new_status": updates.get("followup_status", db_row["followup_status"]),
            })

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  Matched rows:   {len(df_excel) - not_found}")
    print(f"  Not in Supabase: {not_found}")
    print(f"  Rows to update: {len(changes)}")
    print(f"{'=' * 60}")

    if not changes:
        print("\nNo changes detected. Everything is already in sync!")
        return

    # Show changes
    print(f"\nChanges to apply:")
    print(f"{'ID':<8} {'Company':<30} {'Old Status':<20} {'New Status':<20}")
    print("-" * 78)
    for c in changes[:50]:
        company_short = c["company"][:28] if len(c["company"]) > 28 else c["company"]
        print(f"  {c['id']:<8} {company_short:<30} {c['old_status']:<20} {c['new_status']:<20}")
    if len(changes) > 50:
        print(f"  ... and {len(changes) - 50} more changes")

    # Apply updates
    if not args.dry_run:
        print(f"\nUpdating {len(changes)} rows in Supabase...")
        updated = 0
        for c in changes:
            supabase.table("leads").update(c["updates"]).eq("pk", c["pk"]).execute()
            updated += 1
            if updated % 100 == 0:
                print(f"  Updated {updated}/{len(changes)}...")
        print(f"\nDone! {updated} rows updated in Supabase.")
        print("Refresh the website to see the changes.")
    else:
        print(f"\nDRY RUN complete — {len(changes)} rows would be updated.")


if __name__ == "__main__":
    main()
