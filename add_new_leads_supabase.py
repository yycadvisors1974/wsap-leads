"""
add_new_leads_supabase.py — Adds new Power App data to Supabase.

Uses ID + Company Name as composite key for deduplication.
NEVER overwrites existing rows — only appends new ones.

Usage:
    python add_new_leads_supabase.py --new-data "C:/path/to/new_download.xlsx"
    python add_new_leads_supabase.py --new-data "C:/path/to/new_download.xlsx" --dry-run

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

SALESPERSONS = {
    "boonwai.ho@yycadvisors.com": "BOON WAI",
    "chijian.ng@yycadvisors.com": "LUCAS",
    "chilipang@yycadvisors.com": "PANG",
    "sinmee.su@yycadvisors.com": "MIA",
    "karwun.low@yycadvisors.com": "CARMEN",
    "davidng@yycadvisors.com": "DAVID",
    "wanrou.tan@yycadvisors.com": "WAN ROU",
    "ellasoon@yycadvisors.com": "ELLA SOON",
    "soo.yingying@yycadvisors.com": "ESTHER SOO",
    "chuanyau.ngoh@yycadvisors.com": "EDISON",
    "shausong.chong@yycadvisors.com": "IAN",
    "chaiyuen@yycadvisors.com": "JENNY LEE",
    "winhui.teow@yycadvisors.com": "HUI",
    "jiajie.yeow@yycadvisors.com": "YEOW JIA JIE",
    "cheejian.chen@yycadvisors.com": "CJ",
    "chunjie.lim@yycadvisors.com": "JACOB",
}

TEAMS = {
    "PANG'S TEAM": ["PANG", "BOON WAI", "LUCAS"],
    "DAVID'S TEAM": ["DAVID", "WAN ROU"],
    "MIA'S TEAM": ["MIA", "CARMEN"],
    "ELLA'S TEAM": ["ELLA SOON", "ESTHER SOO", "EDISON", "IAN"],
    "TELE": ["CJ", "HUI", "JACOB", "JENNY LEE", "YEOW JIA JIE"],
}

COLUMN_MAP = {
    "ID": "id",
    "Full Name": "full_name",
    "Company Name": "company_name",
    "Contact Number": "contact_number",
    "Email Address": "email_address",
    "Designation": "designation",
    "Sales Person": "sales_person",
    "Reminder Call PIC": "reminder_call_pic",
    "Concern": "concern",
    "Leads": "leads",
    "utm_source": "utm_source",
    "utm_medium": "utm_medium",
    "utm_campaign": "utm_campaign",
    "utm_term": "utm_term",
    "utm_content": "utm_content",
    "Area": "area",
    "Revenue (M)": "revenue_m",
    "HRDC": "hrdc",
    "Reference Link": "reference_link",
    "Industry": "industry",
    "Created": "created_at",
    "Zoom Link": "zoom_link",
    "Confirmation Status": "confirmation_status",
    "Reminder Call Status": "reminder_call_status",
    "Follow-up Status": "followup_status",
    "Conversation Log": "conversation_log",
    "Attendance": "attendance",
    "Preview Date": "preview_date",
    "Sales Person Name": "sales_person_name",
    "Sales Person Team": "sales_person_team",
    "UTM Value": "utm_value",
    "UTM Grouping": "utm_grouping",
    "Topic": "topic",
    "Remarks": "remarks",
    "Duplicate Check": "duplicate_check",
    "Registered": "registered",
    "Attended": "attended",
}

INT_COLS = ("id", "attendance", "registered")
BOOL_COLS = ("leads", "hrdc")
FLOAT_COLS = ("revenue_m", "attended")


def clean_value(val):
    """Convert pandas values to JSON-safe Python types."""
    if val is None:
        return None
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (float, np.floating)):
        try:
            if np.isnan(val) or np.isinf(val):
                return None
        except (TypeError, ValueError):
            pass
        return float(val)
    if isinstance(val, pd.Timestamp):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str):
        val = val.strip()
        if val in ("", "nan", "NaN", "None"):
            return None
        return val
    if pd.isna(val):
        return None
    return val


def clean_phone(val):
    """Convert phone number to text string."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (int, np.integer)):
        return str(val)
    if isinstance(val, float):
        return str(int(val))
    s = str(val).strip()
    if s in ("", "nan"):
        return None
    return s


def row_to_record(row):
    """Convert a DataFrame row to a Supabase-ready dict."""
    record = {}
    for excel_col, db_col in COLUMN_MAP.items():
        val = row.get(excel_col)
        if excel_col == "Contact Number":
            val = clean_phone(val)
        else:
            val = clean_value(val)

        if val is not None:
            if db_col in INT_COLS:
                try:
                    val = int(float(val))
                except (ValueError, TypeError):
                    val = None
            elif db_col in BOOL_COLS:
                try:
                    val = bool(int(float(val))) if not isinstance(val, bool) else val
                except (ValueError, TypeError):
                    val = False
            elif db_col in FLOAT_COLS:
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    val = None

        record[db_col] = val

    # Auto-populate sales_person_name and sales_person_team if missing
    if not record.get("sales_person_name") and record.get("sales_person"):
        email = record["sales_person"].lower()
        name_map = {k.lower(): v for k, v in SALESPERSONS.items()}
        record["sales_person_name"] = name_map.get(email, "")

    if not record.get("sales_person_team") and record.get("sales_person_name"):
        for team, members in TEAMS.items():
            if record["sales_person_name"] in members:
                record["sales_person_team"] = team
                break

    # Default follow-up status
    if not record.get("followup_status"):
        record["followup_status"] = "Yet to call"

    return record


def main():
    parser = argparse.ArgumentParser(description="Add new leads to Supabase.")
    parser.add_argument("--new-data", required=True, help="Path to new Excel download")
    parser.add_argument("--sheet", default=None, help="Sheet name (default: first sheet)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")
    args = parser.parse_args()

    if not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_KEY environment variable first.")
        print('  set SUPABASE_KEY=your_service_role_key_here')
        sys.exit(1)

    print("=" * 60)
    print("WSAP Leads — Add New Leads to Supabase")
    print("=" * 60)
    if args.dry_run:
        print("*** DRY RUN — no data will be inserted ***")

    # Connect
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Read new download
    print(f"\nReading: {args.new_data}")
    if not os.path.exists(args.new_data):
        print(f"ERROR: File not found: {args.new_data}")
        sys.exit(1)

    df_new = pd.read_excel(args.new_data, sheet_name=args.sheet) if args.sheet else pd.read_excel(args.new_data)
    print(f"  Rows in new download: {len(df_new)}")

    # Verify required columns
    required = ["ID", "Company Name", "Sales Person"]
    missing = [c for c in required if c not in df_new.columns]
    if missing:
        print(f"\nERROR: Missing required columns: {missing}")
        sys.exit(1)

    # Get existing keys from Supabase
    print("\nFetching existing leads from Supabase...")
    existing_keys = set()
    offset = 0
    while True:
        resp = supabase.table("leads").select("id,company_name").range(offset, offset + 999).execute()
        for r in resp.data:
            key = f"{r['id']}|{str(r.get('company_name', '')).strip().lower()}"
            existing_keys.add(key)
        if len(resp.data) < 1000:
            break
        offset += 1000
    print(f"  Existing leads in Supabase: {len(existing_keys)}")

    # Find new rows
    new_records = []
    for _, row in df_new.iterrows():
        id_val = str(row.get("ID", "")).strip()
        company = str(row.get("Company Name", "")).strip().lower()
        key = f"{id_val}|{company}"
        if key not in existing_keys:
            new_records.append(row_to_record(row))

    print(f"\n  New leads to add: {len(new_records)}")
    print(f"  Duplicates skipped: {len(df_new) - len(new_records)}")

    if not new_records:
        print("\nNo new leads to add.")
        return

    # Show summary by salesperson
    print("\n" + "-" * 50)
    print(f"{'Salesperson':<20} {'New Leads':>10}")
    print("-" * 50)
    from collections import Counter
    sp_counts = Counter(r.get("sales_person_name", "UNKNOWN") for r in new_records)
    for sp, count in sorted(sp_counts.items()):
        print(f"  {sp:<20} {count:>10}")
    print("-" * 50)
    print(f"  {'TOTAL':<20} {len(new_records):>10}")

    # Insert
    if not args.dry_run:
        print("\nInserting into Supabase...")
        batch_size = 500
        total = 0
        for i in range(0, len(new_records), batch_size):
            batch = new_records[i : i + batch_size]
            supabase.table("leads").insert(batch).execute()
            total += len(batch)
            print(f"  Inserted {total}/{len(new_records)}")
        print(f"\nDone! {total} new leads added to Supabase.")
    else:
        print("\nDRY RUN complete — no data was inserted.")


if __name__ == "__main__":
    main()
