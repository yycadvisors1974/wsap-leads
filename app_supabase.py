"""
WSAP Leads Tracker — Streamlit App with Supabase Backend

Salespersons log in and see only their leads.
They update Follow-up Status & Remarks.
Changes write directly to Supabase.
Admin sees all data + summary dashboard + can edit any field.
Manager sees their team overview + own leads.
"""

import io
import time
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from fpdf import FPDF

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "Yyc1974@Marketing")

# Salesperson passwords: name-based + @ + last 4 digits of phone
SP_PASSWORDS = {
    "PANG": "pang@7747",
    "LUCAS": "lucas@8322",
    "ELLA SOON": "ella@4684",
    "DAVID": "david@1303",
    "BOON WAI": "boonwai@5471",
    "CARMEN": "carmen@3928",
    "ESTHER SOO": "esther@4850",
    "EDISON": "edison@5687",
    "YEOW JIA JIE": "jj@5120",
    "MIA": "mia@0316",
    "HUI": "hui@8468",
    "WAN ROU": "wanrou@0807",
    "IAN": "ian@5687",
    "JENNY LEE": "jenny@8386",
    "JACOB": "jacob@1563",
    "CJ": "cj@0610",
    "BRANDON": "brandon@9106",
}

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
    "zheqin@yycadvisors.com": "BRANDON",
}

TEAMS = {
    "PANG'S TEAM": ["PANG", "BOON WAI", "LUCAS", "BRANDON"],
    "DAVID'S TEAM": ["DAVID", "WAN ROU"],
    "MIA'S TEAM": ["MIA", "CARMEN"],
    "ELLA'S TEAM": ["ELLA SOON", "ESTHER SOO", "EDISON", "IAN"],
    "TELE": ["CJ", "HUI", "JACOB", "JENNY LEE", "YEOW JIA JIE"],
}

TEAM_ORDER = ["PANG'S TEAM", "DAVID'S TEAM", "MIA'S TEAM", "ELLA'S TEAM", "TELE"]

MANAGERS = {
    "PANG": "PANG'S TEAM",
    "DAVID": "DAVID'S TEAM",
    "MIA": "MIA'S TEAM",
    "ELLA SOON": "ELLA'S TEAM",
}

FOLLOWUP_STATUSES = [
    "Yet to call",
    "Unreached",
    "Follow Up",
    "Call Back",
    "Demo set",
    "Demo met, yet to buy",
    "Register for next preview",
    "Potential",
    "Sales",
    "Duplicate",
    "Invalid Number",
    "Rejected",
    "Competitor",
]

MANAGER_STATUSES = ["Potential", "Demo met, yet to buy", "Demo set", "Follow Up"]

NOT_CALLED_STATUSES = ["Yet to call", "Unreached", "Call Back"]

DISPLAY_COLUMNS = [
    "ID", "Full Name", "Company Name", "Contact Number", "Email Address",
    "Designation", "Follow-up Status", "Remarks", "Conversation Log",
    "Preview Date", "Topic", "Attendance", "Concern", "Area", "Industry",
    "Revenue (M)", "Duplicate Check", "Registered", "Attended",
    "UTM Grouping", "UTM Value",
]

# Columns shown by default in salesperson view
SP_DEFAULT_COLUMNS = [
    "Full Name", "Company Name", "Contact Number",
    "Designation", "Follow-up Status", "Remarks",
    "Revenue (M)", "Registered", "Attended",
    "Area", "Concern", "UTM Value",
]

# Supabase column name → Display column name
DB_TO_DISPLAY = {
    "id": "ID",
    "full_name": "Full Name",
    "company_name": "Company Name",
    "contact_number": "Contact Number",
    "email_address": "Email Address",
    "designation": "Designation",
    "sales_person": "Sales Person",
    "reminder_call_pic": "Reminder Call PIC",
    "concern": "Concern",
    "leads": "Leads",
    "utm_source": "utm_source",
    "utm_medium": "utm_medium",
    "utm_campaign": "utm_campaign",
    "utm_term": "utm_term",
    "utm_content": "utm_content",
    "area": "Area",
    "revenue_m": "Revenue (M)",
    "hrdc": "HRDC",
    "reference_link": "Reference Link",
    "industry": "Industry",
    "created_at": "Created",
    "zoom_link": "Zoom Link",
    "confirmation_status": "Confirmation Status",
    "reminder_call_status": "Reminder Call Status",
    "followup_status": "Follow-up Status",
    "conversation_log": "Conversation Log",
    "attendance": "Attendance",
    "preview_date": "Preview Date",
    "sales_person_name": "Sales Person Name",
    "sales_person_team": "Sales Person Team",
    "utm_value": "UTM Value",
    "utm_grouping": "UTM Grouping",
    "topic": "Topic",
    "remarks": "Remarks",
    "duplicate_check": "Duplicate Check",
    "registered": "Registered",
    "attended": "Attended",
    "pk": "pk",
}

DISPLAY_TO_DB = {v: k for k, v in DB_TO_DISPLAY.items()}

# ==============================================================================
# PAGE CONFIG & CSS
# ==============================================================================

st.set_page_config(
    page_title="WSAP Leads Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stMetric {
        background: #f8f9fa;
        padding: 10px 15px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .stMetric label { font-size: 12px !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 700; }
    div[data-testid="stDataFrame"] { border: 1px solid #e0e0e0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# SUPABASE CLIENT
# ==============================================================================


@st.cache_resource
def get_supabase():
    """Create a cached Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ==============================================================================
# DATA
# ==============================================================================


@st.cache_data(ttl=120)
def load_data() -> pd.DataFrame:
    """Load all data from Supabase."""
    supabase = get_supabase()

    # Fetch all rows (Supabase paginates at 1000 by default)
    all_rows = []
    offset = 0
    batch_size = 1000
    while True:
        resp = supabase.table("leads").select("*").range(offset, offset + batch_size - 1).execute()
        rows = resp.data
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < batch_size:
            break
        offset += batch_size

    df = pd.DataFrame(all_rows)

    # Rename columns from DB names to display names
    df = df.rename(columns=DB_TO_DISPLAY)

    # Clean up data
    if "Contact Number" in df.columns:
        df["Contact Number"] = df["Contact Number"].fillna("").astype(str)
    if "Company Name" in df.columns:
        df["Company Name"] = df["Company Name"].fillna("").astype(str)
    if "Sales Person Name" in df.columns:
        df["Sales Person Name"] = df["Sales Person Name"].fillna("")
    if "Sales Person Team" in df.columns:
        df["Sales Person Team"] = df["Sales Person Team"].fillna("")
    if "Follow-up Status" in df.columns:
        df["Follow-up Status"] = df["Follow-up Status"].fillna("Yet to call")
    if "Preview Date" in df.columns:
        dt = pd.to_datetime(df["Preview Date"], errors="coerce")
        df["Preview Date Display"] = dt.dt.strftime("%Y-%m-%d").fillna("")
        df["Event Year"] = dt.dt.year.astype("Int64").astype(str).replace("<NA>", "")
        df["Event Month"] = dt.dt.strftime("%B %Y").fillna("")
        # Build "23/6/2026 (CASH)" label for date filters
        topic_part = df["Topic"].fillna("").astype(str).str.strip()
        has_date = dt.notna()
        df["Event Date Label"] = ""
        if has_date.any():
            day = dt[has_date].dt.day.astype(int).astype(str)
            month = dt[has_date].dt.month.astype(int).astype(str)
            year = dt[has_date].dt.year.astype(int).astype(str)
            df.loc[has_date, "Event Date Label"] = (
                day + "/" + month + "/" + year
                + " (" + topic_part[has_date] + ")"
            )

    df = _compute_dup_reg_att(df)
    return df


def _compute_dup_reg_att(df):
    """Compute Duplicate Check, Registered, Attended via email/phone matching."""
    n = len(df)
    if n == 0:
        return df

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    emails = df["Email Address"].astype(str).str.strip().str.lower().values
    email_map = {}
    for i, e in enumerate(emails):
        if e and e not in ("nan", "none", ""):
            if e in email_map:
                union(i, email_map[e])
            else:
                email_map[e] = i

    phones = df["Contact Number"].astype(str).str.strip().values
    phone_map = {}
    for i, p in enumerate(phones):
        if p and p not in ("nan", "none", ""):
            if p in phone_map:
                union(i, phone_map[p])
            else:
                phone_map[p] = i

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    dup_vals = [""] * n
    reg_vals = [1] * n
    att_vals = [0] * n

    sp_col = df["Sales Person Name"].astype(str).str.strip().values
    att_col = df["Attendance"].astype(str).str.strip().values

    for group in groups.values():
        reg_count = len(group)
        att_count = sum(1 for i in group if att_col[i] == "1")

        sp_names = sorted(set(
            sp_col[i] for i in group
            if sp_col[i] and sp_col[i].lower() not in ("nan", "none", "")
        ))

        dup_label = ""
        if reg_count > 1:
            if len(sp_names) <= 1:
                dup_label = f"Self-dup: {sp_names[0]}" if sp_names else ""
            else:
                dup_label = f"Dup: {' & '.join(sp_names)}"

        for i in group:
            reg_vals[i] = reg_count
            att_vals[i] = att_count
            dup_vals[i] = dup_label

    df = df.copy()
    df["Duplicate Check"] = dup_vals
    df["Registered"] = reg_vals
    df["Attended"] = att_vals
    return df


def save_changes(changes: dict):
    """Save changes to Supabase. changes = {pk: {db_col: new_val, ...}, ...}"""
    supabase = get_supabase()
    for pk, updates in changes.items():
        supabase.table("leads").update(updates).eq("pk", pk).execute()
    load_data.clear()


def get_assigned_leads(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to only leads assigned to the 16 salespersons."""
    sp_emails = [e.lower() for e in SALESPERSONS.keys()]
    return df[df["Sales Person"].str.lower().isin(sp_emails)].copy()


# ==============================================================================
# REASSIGN REQUESTS
# ==============================================================================


@st.cache_data(ttl=30)
def load_reassign_requests(from_email=None, status_filter=None, to_email=None, unseen_only=False):
    """Fetch reassign requests from Supabase (cached 30s)."""
    supabase = get_supabase()
    query = supabase.table("reassign_requests").select("*").order("created_at", desc=True)
    if from_email:
        query = query.eq("from_sp_email", from_email)
    if status_filter:
        query = query.eq("status", status_filter)
    if to_email:
        query = query.eq("to_sp_email", to_email)
    if unseen_only:
        query = query.eq("seen_by_recipient", False)
    resp = query.execute()
    return resp.data


def load_column_prefs(user_email):
    """Fetch saved column preferences for a user."""
    supabase = get_supabase()
    resp = supabase.table("user_preferences").select("column_prefs").eq("user_email", user_email).execute()
    if resp.data and resp.data[0].get("column_prefs"):
        return resp.data[0]["column_prefs"]
    return None


def save_column_prefs(user_email, cols):
    """Upsert column preferences for a user."""
    supabase = get_supabase()
    supabase.table("user_preferences").upsert({
        "user_email": user_email,
        "column_prefs": cols,
        "updated_at": "now()"
    }).execute()


def submit_reassign_request(lead_pk, lead_name, lead_company, from_email, from_name,
                            to_email, to_name, reason, current_status):
    """Submit a reassign request. Returns (success, message)."""
    supabase = get_supabase()

    # Guard: no duplicate pending request for same lead
    existing = supabase.table("reassign_requests").select("id") \
        .eq("lead_pk", lead_pk).eq("status", "Pending").execute()
    if existing.data:
        return False, "A pending request already exists for this lead."

    supabase.table("reassign_requests").insert({
        "lead_pk": lead_pk,
        "lead_name": lead_name,
        "lead_company": lead_company,
        "from_sp_email": from_email,
        "from_sp_name": from_name,
        "to_sp_email": to_email,
        "to_sp_name": to_name,
        "reason": reason,
        "status": "Pending",
        "current_followup_status": current_status,
    }).execute()
    load_reassign_requests.clear()
    return True, "Request submitted! Admin will review it."


def process_reassign_request(request_id, action, reject_reason=None):
    """Approve or reject a reassign request. Returns (success, message)."""
    from datetime import datetime
    supabase = get_supabase()

    # Guard: verify still Pending
    req = supabase.table("reassign_requests").select("*").eq("id", request_id).execute()
    if not req.data:
        return False, "Request not found."
    req = req.data[0]
    if req["status"] != "Pending":
        return False, f"Request already {req['status']}."

    now = datetime.now()

    if action == "Rejected":
        supabase.table("reassign_requests").update({
            "status": "Rejected",
            "reject_reason": reject_reason or "",
            "reviewed_at": now.isoformat(),
        }).eq("id", request_id).execute()
        load_reassign_requests.clear()
        return True, "Request rejected."

    # Approved — update the lead
    lead_pk = req["lead_pk"]
    lead_resp = supabase.table("leads").select("pk,sales_person,remarks").eq("pk", lead_pk).execute()
    if not lead_resp.data:
        supabase.table("reassign_requests").update({
            "status": "Rejected",
            "reject_reason": "Lead no longer exists.",
            "reviewed_at": now.isoformat(),
        }).eq("id", request_id).execute()
        return False, "Lead no longer exists. Request auto-rejected."

    lead = lead_resp.data[0]
    to_email = req["to_sp_email"]
    to_name = req["to_sp_name"]
    from_name = req["from_sp_name"]
    fs = req["current_followup_status"] or ""

    # Find team for target salesperson
    to_team = ""
    for team, members in TEAMS.items():
        if to_name in members:
            to_team = team
            break

    # Build remark: "reassign from david-UR 29/6"
    status_abbr = "UR" if fs == "Unreached" else fs
    remark_suffix = f"reassign from {from_name.lower()}-{status_abbr} {now.day}/{now.month}"
    existing_remarks = lead.get("remarks") or ""
    new_remarks = f"{existing_remarks}, {remark_suffix}".strip(", ") if existing_remarks else remark_suffix

    # Update lead
    save_changes({lead_pk: {
        "sales_person": to_email,
        "sales_person_name": to_name,
        "sales_person_team": to_team,
        "remarks": new_remarks,
    }})

    # Mark request as approved
    supabase.table("reassign_requests").update({
        "status": "Approved",
        "reviewed_at": now.isoformat(),
    }).eq("id", request_id).execute()

    load_reassign_requests.clear()
    return True, f"Approved! Lead reassigned to {to_name}."


def dismiss_reassign_notifications(request_ids):
    """Mark reassign notifications as seen by recipient."""
    supabase = get_supabase()
    for rid in request_ids:
        supabase.table("reassign_requests").update({"seen_by_recipient": True}).eq("id", rid).execute()
    load_reassign_requests.clear()


# ==============================================================================
# CASCADING DATE FILTER
# ==============================================================================


def cascading_date_filter(df: pd.DataFrame, key_prefix: str):
    """Render Year -> Month -> Event Date cascading filters. Returns filtered df."""
    c1, c2, c3 = st.columns(3)

    all_years = sorted([y for y in df["Event Year"].dropna().unique() if y and y != "<NA>"])
    with c1:
        sel_year = st.multiselect("Year", all_years, default=[], placeholder="All years", key=f"{key_prefix}_year")

    df_y = df.copy()
    if sel_year:
        df_y = df_y[df_y["Event Year"].isin(sel_year)]

    # Sort months by underlying date, display in words (e.g., "June 2026")
    month_dates = df_y[["Event Month", "Preview Date Display"]].dropna().drop_duplicates("Event Month")
    month_dates = month_dates[month_dates["Event Month"] != ""]
    month_sorted = month_dates.sort_values("Preview Date Display")["Event Month"].tolist()
    with c2:
        sel_month = st.multiselect("Month", month_sorted, default=[], placeholder="All months", key=f"{key_prefix}_month")

    df_m = df_y.copy()
    if sel_month:
        df_m = df_m[df_m["Event Month"].isin(sel_month)]

    # Sort date labels by underlying date, display with topic (e.g., "23/6/2026 (CASH)")
    date_labels = df_m[["Event Date Label", "Preview Date Display"]].dropna().drop_duplicates("Event Date Label")
    date_labels = date_labels[date_labels["Event Date Label"] != ""]
    date_sorted = date_labels.sort_values("Preview Date Display")["Event Date Label"].tolist()
    with c3:
        sel_date = st.multiselect("Event Date", date_sorted, default=[], placeholder="All dates", key=f"{key_prefix}_date")

    df_result = df_m.copy()
    if sel_date:
        df_result = df_result[df_result["Event Date Label"].isin(sel_date)]

    return df_result


# ==============================================================================
# HELPER: BUILD CALLING STATUS SUMMARY
# ==============================================================================


def build_calling_summary(df: pd.DataFrame, teams_to_show=None, statuses=None):
    """Build calling status summary grouped by team."""
    if teams_to_show is None:
        teams_to_show = TEAM_ORDER
    if statuses is None:
        statuses = FOLLOWUP_STATUSES

    rows = []
    grand_totals = {s: 0 for s in statuses}
    grand_totals["Total"] = 0

    for team in teams_to_show:
        members = TEAMS.get(team, [])
        team_totals = {s: 0 for s in statuses}
        team_totals["Total"] = 0

        for member in sorted(members):
            member_df = df[df["Sales Person Name"] == member]
            row = {"Sales Person": member}
            row_total = 0
            for status in statuses:
                count = int(len(member_df[member_df["Follow-up Status"] == status]))
                row[status] = count
                team_totals[status] += count
                grand_totals[status] += count
                row_total += count
            row["Total"] = row_total
            team_totals["Total"] += row_total
            grand_totals["Total"] += row_total
            rows.append(row)

        team_row = {"Sales Person": f"{team} Total"}
        for s in statuses:
            team_row[s] = team_totals[s]
        team_row["Total"] = team_totals["Total"]
        rows.append(team_row)

    grand_row = {"Sales Person": "GRAND TOTAL"}
    for s in statuses:
        grand_row[s] = grand_totals[s]
    grand_row["Total"] = grand_totals["Total"]
    rows.append(grand_row)

    return pd.DataFrame(rows)


def style_summary_table(df: pd.DataFrame):
    """Style calling summary with highlighted team subtotal and grand total rows."""
    def row_style(row):
        sp = str(row["Sales Person"])
        if "GRAND TOTAL" in sp:
            return ["background-color: #1f4e79; color: white; font-weight: bold"] * len(row)
        elif "Total" in sp:
            return ["background-color: #d6e4f0; font-weight: bold"] * len(row)
        return [""] * len(row)
    return df.style.apply(row_style, axis=1)


def _build_calling_status_pdf(summary_df, statuses, filter_desc, teams_show, df_cs):
    """Generate a landscape PDF of calling status summary with text wrapping."""
    from datetime import datetime
    from fpdf.enums import XPos, YPos

    NL = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}  # shortcut for newline

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Calling Status for {filter_desc}", align="C", **NL)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Date generated: {datetime.now().strftime('%d/%m/%Y %I:%M %p')}", align="C", **NL)
    pdf.ln(4)

    columns = ["Sales Person"] + list(statuses) + ["Total"]
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    first_col_w = 32
    remaining_w = page_w - first_col_w
    n_data_cols = len(columns) - 1
    data_col_w = remaining_w / n_data_cols if n_data_cols > 0 else remaining_w
    col_widths = [first_col_w] + [data_col_w] * n_data_cols

    row_h = 7

    def _draw_header():
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_fill_color(31, 78, 121)
        pdf.set_text_color(255, 255, 255)
        for i, col in enumerate(columns):
            label = col[:12] if len(col) > 12 else col
            align = "L" if i == 0 else "C"
            pdf.cell(col_widths[i], row_h, label, border=1, fill=True, align=align)
        pdf.ln(row_h)
        pdf.set_text_color(0, 0, 0)

    def _draw_row(row_data, is_total=False, is_grand=False):
        if is_grand:
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(31, 78, 121)
            pdf.set_text_color(255, 255, 255)
        elif is_total:
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(214, 228, 240)
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.set_font("Helvetica", "", 7)
            pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(0, 0, 0)

        for i, col in enumerate(columns):
            val = str(row_data.get(col, ""))
            if val == "0" and not is_total and not is_grand:
                val = "-"
            align = "L" if i == 0 else "C"
            pdf.cell(col_widths[i], row_h, val, border=1, fill=True, align=align)
        pdf.ln(row_h)
        pdf.set_text_color(0, 0, 0)

    # --- Section 1: Team Overview (team totals only) ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Team Overview", **NL)
    pdf.ln(2)

    _draw_header()
    for team in teams_show:
        team_total_row = summary_df[summary_df["Sales Person"] == f"{team} Total"]
        if not team_total_row.empty:
            row_data = team_total_row.iloc[0].to_dict()
            row_data["Sales Person"] = team
            _draw_row(row_data, is_total=True)

    grand_rows = summary_df[summary_df["Sales Person"] == "GRAND TOTAL"]
    if not grand_rows.empty:
        _draw_row(grand_rows.iloc[0].to_dict(), is_grand=True)
    pdf.ln(6)

    # --- Section 2: Calling Status Breakdown (per team, per person) ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Calling Status Breakdown", **NL)
    pdf.ln(2)

    for team in teams_show:
        if pdf.get_y() > pdf.h - 40:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, team, **NL)
        _draw_header()

        members = TEAMS.get(team, [])
        for _, row in summary_df.iterrows():
            sp = str(row["Sales Person"])
            if sp in members:
                _draw_row(row.to_dict())
            elif sp == f"{team} Total":
                _draw_row(row.to_dict(), is_total=True)

        pdf.ln(3)

    if not grand_rows.empty:
        if pdf.get_y() > pdf.h - 25:
            pdf.add_page()
        _draw_header()
        _draw_row(grand_rows.iloc[0].to_dict(), is_grand=True)

    return bytes(pdf.output())


# ==============================================================================
# KPI CARD
# ==============================================================================


def render_team_kpi_card(df_team: pd.DataFrame, team_name: str, target_pct: int):
    """Render a screenshot-friendly KPI card for a team."""
    total = len(df_team)
    not_called = len(df_team[df_team["Follow-up Status"].isin(NOT_CALLED_STATUSES)])
    called = total - not_called
    calling_pct = round(called / total * 100) if total > 0 else 0
    target_count = round(total * target_pct / 100)

    if calling_pct >= target_pct:
        light = "🟢"
    elif calling_pct >= target_pct * 0.5:
        light = "🟡"
    else:
        light = "🔴"

    display_name = team_name.replace("'S TEAM", "'s Team").title() if "TEAM" in team_name else team_name.title()

    members = TEAMS.get(team_name, [])
    person_parts = []
    for member in sorted(members):
        m_df = df_team[df_team["Sales Person Name"] == member]
        m_total = len(m_df)
        m_not_called = len(m_df[m_df["Follow-up Status"].isin(NOT_CALLED_STATUSES)])
        m_called = m_total - m_not_called
        person_parts.append(f"{member}: {m_called}")
    person_line = " | ".join(person_parts)

    st.markdown(f"""
    <div style="background: #1a1a2e; color: #e0e0e0; padding: 24px 32px; border-radius: 12px;
                margin-bottom: 16px; text-align: center; font-family: sans-serif;">
        <div style="font-size: 20px; font-weight: 700; margin-bottom: 12px; color: #ffffff;">
            {display_name}
        </div>
        <div style="font-size: 15px; line-height: 2;">
            Total Leads : <b>{total}</b><br>
            Target of Calling Rate : <b>{target_count} ({target_pct}%)</b><br>
            Calling Rate Result : <b>{called} ({calling_pct}%)</b> {light}<br>
            UR, Call Back, Yet to Call : <b>{not_called}</b>
        </div>
        <div style="font-size: 12px; color: #aab; margin-top: 8px;">
            No. of Leads Called : {person_line}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# LOGIN
# ==============================================================================


def login_page():
    st.markdown("""
    <div style="text-align: center; padding: 60px 0 30px 0;">
        <h1 style="font-size: 2.5em; margin-bottom: 5px;">WSAP Leads Tracker</h1>
        <p style="color: #888; font-size: 1.1em;">Sign in to access your leads</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.2, 1.5, 1.2])
    with col2:
        with st.container(border=True):
            st.markdown("#### Sign In")
            options = ["-- Select your name --"] + sorted(SALESPERSONS.values()) + ["ADMIN"]
            selected = st.selectbox("Who are you?", options, label_visibility="collapsed")
            password = st.text_input("Password", type="password")
            submitted = st.button("Sign In", use_container_width=True, type="primary")

            if submitted:
                if selected == "-- Select your name --":
                    st.error("Please select your name.")
                elif selected == "ADMIN":
                    if password == ADMIN_PASSWORD:
                        st.session_state.update(user_email="admin", user_name="ADMIN", is_admin=True, is_manager=False)
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                else:
                    email = [e for e, n in SALESPERSONS.items() if n == selected][0]
                    expected_pw = SP_PASSWORDS.get(selected, "")
                    if password == expected_pw:
                        st.session_state.update(
                            user_email=email, user_name=selected, is_admin=False,
                            is_manager=selected in MANAGERS,
                            manager_team=MANAGERS.get(selected, ""),
                        )
                        st.rerun()
                    else:
                        st.error("Incorrect password.")


# ==============================================================================
# SALESPERSON VIEW
# ==============================================================================


def salesperson_view(user_email: str, user_name: str, show_header: bool = True):
    if show_header:
        hcol1, hcol2 = st.columns([3, 1])
        with hcol1:
            st.markdown(f"## {user_name}'s Leads")
        with hcol2:
            st.button("Refresh", on_click=load_data.clear, key="sp_refresh")

    df_full = load_data()
    df_sp = df_full[df_full["Sales Person"].str.lower() == user_email.lower()].copy()

    # --- One-time banner for newly reassigned leads ---
    unseen = load_reassign_requests(to_email=user_email, status_filter="Approved", unseen_only=True)
    if unseen:
        lead_names = ", ".join(f"{r['lead_name']} ({r['lead_company']})" for r in unseen[:5])
        extra = f" and {len(unseen) - 5} more" if len(unseen) > 5 else ""
        st.info(f"📋 **{len(unseen)} lead(s) recently reassigned to you:** {lead_names}{extra}")
        if st.button("Dismiss", key=f"dismiss_reassign_{user_email}"):
            dismiss_reassign_notifications([r["id"] for r in unseen])
            st.rerun()

    if df_sp.empty:
        st.warning("No leads found for your account.")
        return

    # Show pending reassign count in tab label
    my_pending = load_reassign_requests(from_email=user_email, status_filter="Pending")
    pending_label = f"Request Reassign ({len(my_pending)})" if my_pending else "Request Reassign"
    sp_tab_leads, sp_tab_reassign = st.tabs(["My Leads", pending_label])

    with sp_tab_reassign:
        st.markdown("### Bulk Reassign Leads")

        if my_pending:
            st.caption(f"You have **{len(my_pending)}** pending request(s) awaiting admin approval.")

        # --- Filter row ---
        bf1, bf2 = st.columns(2)
        with bf1:
            bulk_status = st.multiselect(
                "Filter by Status", FOLLOWUP_STATUSES, default=[],
                placeholder="Select status to filter", key=f"bulk_status_{user_email}"
            )
        with bf2:
            sp_month_dates_ra = df_sp[["Event Month", "Preview Date Display"]].dropna().drop_duplicates("Event Month")
            sp_month_dates_ra = sp_month_dates_ra[sp_month_dates_ra["Event Month"] != ""]
            sp_months_ra = sp_month_dates_ra.sort_values("Preview Date Display")["Event Month"].tolist()
            bulk_month = st.multiselect(
                "Filter by Month", sp_months_ra, default=[],
                placeholder="All months", key=f"bulk_month_{user_email}"
            )

        # Apply filters
        df_bulk = df_sp.copy()
        if bulk_status:
            df_bulk = df_bulk[df_bulk["Follow-up Status"].isin(bulk_status)]
        if bulk_month:
            df_bulk = df_bulk[df_bulk["Event Month"].isin(bulk_month)]

        if bulk_status or bulk_month:
            # Get existing pending lead_pks to exclude
            pending_pks = set()
            if my_pending:
                pending_pks = {r["lead_pk"] for r in my_pending}

            # Build checkbox table
            bulk_table = df_bulk[["pk", "ID", "Full Name", "Company Name", "Contact Number",
                                  "Event Date Label", "Follow-up Status"]].copy()
            bulk_table.insert(0, "Select", False)
            # Mark already-pending leads
            if pending_pks:
                bulk_table.loc[bulk_table["pk"].isin(pending_pks), "Select"] = None

            st.caption(f"**{len(bulk_table)}** leads match your filters. Tick the ones to reassign, then click Submit.")

            with st.form(key=f"bulk_form_{user_email}"):
                edited_bulk = st.data_editor(
                    bulk_table,
                    column_config={
                        "pk": None,
                        "Select": st.column_config.CheckboxColumn("✓", width="small"),
                        "ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                        "Full Name": st.column_config.TextColumn("Name", disabled=True, width="medium"),
                        "Company Name": st.column_config.TextColumn("Company", disabled=True, width="medium"),
                        "Contact Number": st.column_config.TextColumn("Phone", disabled=True, width="small"),
                        "Event Date Label": st.column_config.TextColumn("Event", disabled=True, width="medium"),
                        "Follow-up Status": st.column_config.TextColumn("Status", disabled=True, width="small"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    key=f"bulk_editor_{user_email}",
                )

                sp_names = sorted([n for n in SALESPERSONS.values() if n != user_name])
                bulk_target = st.selectbox("Reassign to", sp_names, key=f"bulk_target_{user_email}")
                bulk_reason = st.text_input("Reason (required)", "", key=f"bulk_reason_{user_email}")

                submitted = st.form_submit_button("Submit Request(s)", type="primary")

            if submitted:
                selected_rows = edited_bulk[edited_bulk["Select"] == True]
                selected_count = len(selected_rows)
                if selected_count == 0:
                    st.warning("No leads selected.")
                elif not bulk_reason.strip():
                    st.error("Please provide a reason.")
                else:
                    to_email_addr = [e for e, n in SALESPERSONS.items() if n == bulk_target][0]
                    success_count = 0
                    skip_count = 0
                    for _, row in selected_rows.iterrows():
                        ok, msg = submit_reassign_request(
                            lead_pk=int(row["pk"]),
                            lead_name=str(row["Full Name"]),
                            lead_company=str(row["Company Name"]),
                            from_email=user_email,
                            from_name=user_name,
                            to_email=to_email_addr,
                            to_name=bulk_target,
                            reason=bulk_reason.strip(),
                            current_status=str(row.get("Follow-up Status", "")),
                        )
                        if ok:
                            success_count += 1
                        else:
                            skip_count += 1
                    msg_parts = [f"{success_count} request(s) submitted!"]
                    if skip_count:
                        msg_parts.append(f"{skip_count} skipped (already pending).")
                    st.success(" ".join(msg_parts))
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Select a status filter above to see leads for reassignment.")

        # --- Single search fallback ---
        with st.expander("Search for a specific lead"):
            ra_search = st.text_input(
                "Search (name, company, phone, or ID)", "", key=f"ra_search_{user_email}"
            )

            if ra_search:
                s = ra_search.strip()
                words = s.lower().split()
                ra_combined = (
                    df_sp["Full Name"].astype(str) + " " +
                    df_sp["Company Name"].astype(str) + " " +
                    df_sp["Contact Number"].astype(str) + " " +
                    df_sp["ID"].astype(str)
                ).str.lower()
                ra_mask = ra_combined.apply(lambda x: all(w in x for w in words))
                ra_results = df_sp[ra_mask].head(20)

                if ra_results.empty:
                    st.info("No matching leads found.")
                else:
                    lead_options = {}
                    for _, r in ra_results.iterrows():
                        event = str(r.get("Event Date Label", "")).strip()
                        event_part = f" | {event}" if event else ""
                        label = f"{int(r['ID'])} - {r['Full Name']} ({r['Company Name']}) - {r['Contact Number']}{event_part}"
                        lead_options[label] = r
                    selected_lead = st.selectbox(
                        "Select lead", list(lead_options.keys()), key=f"ra_lead_{user_email}"
                    )

                    sp_names_s = sorted([n for n in SALESPERSONS.values() if n != user_name])
                    target_sp = st.selectbox("Reassign to", sp_names_s, key=f"ra_target_{user_email}")
                    ra_reason = st.text_input("Reason (required)", "", key=f"ra_reason_{user_email}")

                    if st.button("Submit Request", key=f"ra_submit_{user_email}", type="primary"):
                        if not ra_reason.strip():
                            st.error("Please provide a reason.")
                        else:
                            lead_row = lead_options[selected_lead]
                            to_email_addr = [e for e, n in SALESPERSONS.items() if n == target_sp][0]
                            success, msg = submit_reassign_request(
                                lead_pk=int(lead_row["pk"]),
                                lead_name=str(lead_row["Full Name"]),
                                lead_company=str(lead_row["Company Name"]),
                                from_email=user_email,
                                from_name=user_name,
                                to_email=to_email_addr,
                                to_name=target_sp,
                                reason=ra_reason.strip(),
                                current_status=str(lead_row.get("Follow-up Status", "")),
                            )
                            if success:
                                st.success(msg)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning(msg)

    with sp_tab_leads:
        # --- Filters Row 1 ---
        fcol0a, fcol0b, fcol0c, fcol0d = st.columns(4)
        with fcol0a:
            attend_filter = st.selectbox(
                "Attendance", ["Attended (1)", "Not Attended (0)", "All"], key="sp_attend"
            )
        with fcol0b:
            status_filter = st.multiselect(
                "Filter by Status", FOLLOWUP_STATUSES, default=[], placeholder="All statuses", key="sp_status"
            )
        with fcol0c:
            # Month filter (words, e.g., "June 2026")
            sp_month_dates = df_sp[["Event Month", "Preview Date Display"]].dropna().drop_duplicates("Event Month")
            sp_month_dates = sp_month_dates[sp_month_dates["Event Month"] != ""]
            sp_months_sorted = sp_month_dates.sort_values("Preview Date Display")["Event Month"].tolist()
            month_filter = st.multiselect(
                "Month", sp_months_sorted, default=[], placeholder="All months", key="sp_month"
            )
        with fcol0d:
            # Cascading: filter by month first to populate event date options
            df_sp_month = df_sp.copy()
            if month_filter:
                df_sp_month = df_sp_month[df_sp_month["Event Month"].isin(month_filter)]
            sp_date_labels = df_sp_month[["Event Date Label", "Preview Date Display"]].dropna().drop_duplicates("Event Date Label")
            sp_date_labels = sp_date_labels[sp_date_labels["Event Date Label"] != ""]
            sp_dates_sorted = sp_date_labels.sort_values("Preview Date Display")["Event Date Label"].tolist()
            event_filter = st.multiselect(
                "Event Date", sp_dates_sorted, default=[], placeholder="All dates", key="sp_event"
            )

        # --- Filters Row 2 ---
        available_cols = [c for c in DISPLAY_COLUMNS if c in df_sp.columns]
        saved_prefs = load_column_prefs(user_email)
        if saved_prefs:
            default_cols = [c for c in saved_prefs if c in available_cols]
            if not default_cols:
                default_cols = [c for c in SP_DEFAULT_COLUMNS if c in available_cols]
        else:
            default_cols = [c for c in SP_DEFAULT_COLUMNS if c in available_cols]
        fcol4, fcol4b, fcol5, fcol6 = st.columns(4)
        with fcol4:
            utm_group_values = sorted(df_sp["UTM Grouping"].dropna().astype(str).str.strip().unique())
            utm_group_values = [v for v in utm_group_values if v and v.lower() not in ("nan", "none", "")]
            utm_group_filter = st.multiselect(
                "Source", utm_group_values, default=[], placeholder="All sources", key="sp_utm_group"
            )
        with fcol4b:
            concern_values = sorted(df_sp["Concern"].dropna().astype(str).str.strip().unique())
            concern_values = [c for c in concern_values if c and c.lower() not in ("nan", "none", "")]
            concern_filter = st.multiselect(
                "Concern", concern_values, default=[], placeholder="All concerns", key="sp_concern"
            )
        with fcol5:
            search = st.text_input("Search (name, company, phone, or log)", "", key="sp_search")
        with fcol6:
            selected_cols = st.multiselect(
                "Columns to show", available_cols, default=default_cols, key="sp_cols"
            )
            if selected_cols != default_cols:
                save_column_prefs(user_email, selected_cols)

        # --- Apply Filters ---
        df_display = df_sp.copy()
        if attend_filter == "Attended (1)":
            df_display = df_display[df_display["Attendance"] == 1]
        elif attend_filter == "Not Attended (0)":
            df_display = df_display[df_display["Attendance"] == 0]

        # --- Status Summary Cards (reflects attendance filter) ---
        status_counts = df_display["Follow-up Status"].value_counts()
        total = len(df_display)
        card_statuses = ["Yet to call", "Unreached", "Follow Up", "Call Back", "Demo set", "Potential", "Sales"]
        cols = st.columns(len(card_statuses))
        for i, status in enumerate(card_statuses):
            cols[i].metric(status, status_counts.get(status, 0))
        st.caption(f"Total: **{total}** leads")
        st.divider()
        if month_filter:
            df_display = df_display[df_display["Event Month"].isin(month_filter)]
        if status_filter:
            df_display = df_display[df_display["Follow-up Status"].isin(status_filter)]
        if event_filter:
            df_display = df_display[df_display["Event Date Label"].isin(event_filter)]
        if utm_group_filter:
            df_display = df_display[df_display["UTM Grouping"].astype(str).str.strip().isin(utm_group_filter)]
        if concern_filter:
            df_display = df_display[df_display["Concern"].astype(str).str.strip().isin(concern_filter)]
        if search:
            s = search.strip()
            mask = (
                df_display["Full Name"].astype(str).str.contains(s, case=False, na=False)
                | df_display["Company Name"].astype(str).str.contains(s, case=False, na=False)
                | df_display["Contact Number"].astype(str).str.contains(s, case=False, na=False)
                | df_display["Conversation Log"].astype(str).str.contains(s, case=False, na=False)
            )
            df_display = df_display[mask]

        show_cols = selected_cols if selected_cols else default_cols
        df_edit = df_display[["pk"] + show_cols].copy()

        # --- Export button ---
        from datetime import date
        sp_export = df_display[[c for c in DISPLAY_COLUMNS if c in df_display.columns]].copy()
        sp_buffer = io.BytesIO()
        sp_export.to_excel(sp_buffer, index=False, sheet_name="My Leads")
        sp_buffer.seek(0)
        st.download_button(
            label=f"Export My Leads ({len(sp_export)} rows)",
            data=sp_buffer,
            file_name=f"My_Leads_{user_name}_{date.today().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="sp_export_btn",
        )

        st.markdown(f"**Showing {len(df_edit)} leads** — edit Follow-up Status & Remarks, then click Save.")

        # --- Editable Table ---
        with st.form(key=f"sp_edit_form_{user_email}"):
            edited_df = st.data_editor(
                df_edit,
                column_config={
                    "pk": None,  # Hidden
                    "ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "Full Name": st.column_config.TextColumn("Full Name", disabled=True, width="medium"),
                    "Company Name": st.column_config.TextColumn("Company", disabled=True, width="medium"),
                    "Contact Number": st.column_config.TextColumn("Phone", disabled=True, width="small"),
                    "Email Address": st.column_config.TextColumn("Email", disabled=True, width="medium"),
                    "Designation": st.column_config.TextColumn("Designation", disabled=True, width="small"),
                    "Follow-up Status": st.column_config.SelectboxColumn(
                        "Follow-up Status", options=FOLLOWUP_STATUSES, required=True, width="medium",
                    ),
                    "Remarks": st.column_config.TextColumn("Remarks", width="small"),
                    "Conversation Log": st.column_config.TextColumn("Log", disabled=True, width="medium"),
                    "Preview Date": st.column_config.TextColumn("Event Date", disabled=True, width="small"),
                    "Topic": st.column_config.TextColumn("Topic", disabled=True, width="small"),
                    "Attendance": st.column_config.TextColumn("Attend", disabled=True, width="small"),
                    "Concern": st.column_config.TextColumn("Concern", disabled=True, width="medium"),
                    "Area": st.column_config.TextColumn("Area", disabled=True, width="small"),
                    "Industry": st.column_config.TextColumn("Industry", disabled=True, width="small"),
                    "Revenue (M)": st.column_config.NumberColumn("Revenue (M)", disabled=True, width="small"),
                    "Duplicate Check": st.column_config.TextColumn("Dup Chk", disabled=True, width="small"),
                    "Registered": st.column_config.NumberColumn("Registered", disabled=True, width="small"),
                    "Attended": st.column_config.NumberColumn("Attended", disabled=True, width="small"),
                },
                use_container_width=True,
                num_rows="fixed",
                hide_index=True,
                key=f"sp_editor_{user_email}",
            )

            submitted = st.form_submit_button("Save Changes", type="primary", use_container_width=True)

        if submitted:
            changes = {}
            for i in range(len(df_edit)):
                orig_row = df_edit.iloc[i]
                edit_row = edited_df.iloc[i]
                orig_status = str(orig_row.get("Follow-up Status", ""))
                edit_status = str(edit_row.get("Follow-up Status", ""))
                orig_remarks = str(orig_row.get("Remarks", ""))
                edit_remarks = str(edit_row.get("Remarks", ""))

                if orig_status != edit_status or orig_remarks != edit_remarks:
                    pk = int(orig_row["pk"])
                    updates = {}
                    if orig_status != edit_status:
                        updates["followup_status"] = edit_status
                    if orig_remarks != edit_remarks:
                        updates["remarks"] = edit_remarks if edit_remarks != "nan" else None
                    changes[pk] = updates

            if changes:
                with st.spinner(f"Saving {len(changes)} change(s)..."):
                    try:
                        save_changes(changes)
                        st.success(f"{len(changes)} change(s) saved!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving: {e}")
            else:
                st.info("No changes detected.")



# ==============================================================================
# MANAGER VIEW
# ==============================================================================


def manager_view(user_email: str, user_name: str, team_name: str):
    hcol1, hcol2 = st.columns([3, 1])
    with hcol1:
        st.markdown(f"## {user_name} — {team_name}")
    with hcol2:
        st.button("Refresh", on_click=load_data.clear, key="mgr_refresh")

    tab_leads, tab_team = st.tabs(["My Leads", "Team Overview"])

    with tab_leads:
        salesperson_view(user_email, user_name, show_header=False)

    with tab_team:
        df_full = load_data()
        df_assigned = get_assigned_leads(df_full)

        team_members = TEAMS.get(team_name, [])
        df_team = df_assigned[df_assigned["Sales Person Name"].isin(team_members)].copy()

        mgr_attend = st.selectbox(
            "Attendance", ["Attended (1)", "Not Attended (0)", "All"], key="mgr_attend"
        )

        df_team = cascading_date_filter(df_team, "mgr")

        if mgr_attend == "Attended (1)":
            df_team = df_team[df_team["Attendance"] == 1]
        elif mgr_attend == "Not Attended (0)":
            df_team = df_team[df_team["Attendance"] == 0]

        st.caption(f"**{len(df_team)}** leads across **{len(team_members)}** team members")

        st.markdown("### Manager's Table")
        mgr_table = build_calling_summary(df_team, teams_to_show=[team_name], statuses=MANAGER_STATUSES)
        st.dataframe(style_summary_table(mgr_table), use_container_width=True, hide_index=True)

        st.markdown("### Calling Status Summary")
        call_summary = build_calling_summary(df_team, teams_to_show=[team_name])
        st.dataframe(style_summary_table(call_summary), use_container_width=True, hide_index=True)

        st.markdown("### Team KPI")
        render_team_kpi_card(df_team, team_name, 70)


# ==============================================================================
# ADMIN VIEW
# ==============================================================================


def admin_view():
    hcol1, hcol2 = st.columns([3, 1])
    with hcol1:
        st.markdown("## Admin Dashboard")
    with hcol2:
        st.button("Refresh", on_click=load_data.clear, key="admin_refresh")

    df_full = load_data()
    df = df_full.copy()

    st.caption(f"**{len(df)}** total leads")

    # Fetch pending reassign count for tab label
    pending_reassign = load_reassign_requests(status_filter="Pending")
    pending_count = len(pending_reassign)
    reassign_label = f"Reassign Requests ({pending_count})" if pending_count else "Reassign Requests"

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Calling Status", "All Leads", "Charts", "Daily Report", "Upload New Leads", reassign_label
    ])

    # ==================================================================
    # TAB 1: CALLING STATUS SUMMARY
    # ==================================================================
    with tab1:
        f1, f2 = st.columns(2)
        with f1:
            cs_team = st.multiselect(
                "Filter by Team", TEAM_ORDER, default=[], placeholder="All teams", key="cs_team"
            )
        with f2:
            cs_attendance = st.selectbox(
                "Attendance", ["All", "Attended (1)", "Not Attended (0)"], key="cs_attend"
            )

        df_cs = cascading_date_filter(df, "cs")

        if cs_attendance == "Attended (1)":
            df_cs = df_cs[df_cs["Attendance"] == 1]
        elif cs_attendance == "Not Attended (0)":
            df_cs = df_cs[df_cs["Attendance"] == 0]

        selected_statuses = st.multiselect(
            "Select statuses to display",
            FOLLOWUP_STATUSES,
            default=FOLLOWUP_STATUSES,
            key="cs_statuses",
        )

        teams_show = cs_team if cs_team else TEAM_ORDER
        if selected_statuses:
            call_summary = build_calling_summary(df_cs, teams_to_show=teams_show, statuses=selected_statuses)

            # --- Build filter description for PDF title ---
            sel_months = st.session_state.get("cs_month", [])
            sel_dates = st.session_state.get("cs_date", [])
            if sel_dates:
                filter_desc = ", ".join(sel_dates)
            elif sel_months:
                filter_desc = ", ".join(sel_months)
            else:
                filter_desc = "All Events"

            # --- Expandable by-team view ---
            st.markdown("#### Calling Status by Team")
            for team in teams_show:
                members = TEAMS.get(team, [])
                team_rows = call_summary[call_summary["Sales Person"].isin(members + [f"{team} Total"])]
                team_total_row = call_summary[call_summary["Sales Person"] == f"{team} Total"]
                total_val = int(team_total_row["Total"].values[0]) if not team_total_row.empty else 0
                with st.expander(f"{team} — {total_val} leads"):
                    st.dataframe(style_summary_table(team_rows), use_container_width=True, hide_index=True)

            # Grand total
            grand_row = call_summary[call_summary["Sales Person"] == "GRAND TOTAL"]
            if not grand_row.empty:
                st.dataframe(style_summary_table(grand_row), use_container_width=True, hide_index=True)

            # --- Full table (collapsed) ---
            with st.expander("View full table"):
                st.dataframe(style_summary_table(call_summary), use_container_width=True, hide_index=True, height=700)

            # --- PDF Download ---
            st.divider()
            pdf_bytes = _build_calling_status_pdf(call_summary, selected_statuses, filter_desc, teams_show, df_cs)
            st.download_button(
                label="Download Calling Status as PDF",
                data=pdf_bytes,
                file_name=f"Calling_Status_{filter_desc.replace('/', '-').replace(' ', '_')}.pdf",
                mime="application/pdf",
                key="cs_pdf_download",
                type="primary",
            )
        else:
            st.info("Select at least one status to display.")

    # ==================================================================
    # TAB 2: ALL LEADS
    # ==================================================================
    with tab2:
        # --- Export Button at top ---
        df_export_base = df.copy()
        drop_cols = ["pk", "Preview Date Display", "Event Year", "Event Month", "Event Date Label"]
        df_export_base = df_export_base.drop(columns=[c for c in drop_cols if c in df_export_base.columns])
        buffer = io.BytesIO()
        df_export_base.to_excel(buffer, index=False, sheet_name="Leads")
        buffer.seek(0)
        from datetime import date as _date
        st.download_button(
            label=f"Export All to Excel ({len(df_export_base)} rows)",
            data=buffer,
            file_name=f"WSAP_Leads_Export_{_date.today().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="al_export_btn",
        )

        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            all_sp_names = sorted(df["Sales Person Name"].dropna().unique())
            all_sp_names = [n for n in all_sp_names if n.strip()]
            sp_filter = st.multiselect(
                "Salesperson", all_sp_names, default=[], placeholder="All", key="al_sp"
            )
        with fcol2:
            st_filter = st.multiselect(
                "Status", FOLLOWUP_STATUSES, default=[], placeholder="All", key="al_st"
            )
        with fcol3:
            al_team = st.multiselect(
                "Team", TEAM_ORDER + ["Unassigned"], default=[], placeholder="All", key="al_team"
            )

        df_al = cascading_date_filter(df, "al")

        search = st.text_input("Search name, company, or phone number", "", key="al_search")

        df_v = df_al.copy()
        if sp_filter:
            df_v = df_v[df_v["Sales Person Name"].isin(sp_filter)]
        if st_filter:
            df_v = df_v[df_v["Follow-up Status"].isin(st_filter)]
        if al_team:
            team_members = []
            include_unassigned = False
            for t in al_team:
                if t == "Unassigned":
                    include_unassigned = True
                else:
                    team_members.extend(TEAMS.get(t, []))
            if include_unassigned and team_members:
                df_v = df_v[(df_v["Sales Person Name"].isin(team_members)) | (df_v["Sales Person Name"] == "")]
            elif include_unassigned:
                df_v = df_v[df_v["Sales Person Name"] == ""]
            else:
                df_v = df_v[df_v["Sales Person Name"].isin(team_members)]
        if search:
            s = search.strip()
            m = (
                df_v["Full Name"].astype(str).str.contains(s, case=False, na=False)
                | df_v["Company Name"].astype(str).str.contains(s, case=False, na=False)
                | df_v["Contact Number"].astype(str).str.contains(s, case=False, na=False)
            )
            df_v = df_v[m]

        show_cols = ["Sales Person Name", "Sales Person Team"] + [c for c in DISPLAY_COLUMNS if c in df_v.columns]
        st.dataframe(df_v[show_cols], use_container_width=True, hide_index=True, height=600)
        st.caption(f"Showing {len(df_v)} of {len(df)}")

        # --- Edit Salesperson ---
        st.divider()
        st.markdown("#### Reassign Salesperson")
        edit_search = st.text_input("Search by name, company, phone, or ID to edit", "", key="edit_search")

        if edit_search:
            s = edit_search.strip()
            mask = (
                df_full["Full Name"].astype(str).str.contains(s, case=False, na=False)
                | df_full["Company Name"].astype(str).str.contains(s, case=False, na=False)
                | df_full["Contact Number"].astype(str).str.contains(s, case=False, na=False)
                | df_full["ID"].astype(str).str.contains(s, case=False, na=False)
            )
            df_results = df_full[mask].head(20)

            if df_results.empty:
                st.info("No leads found.")
            else:
                st.caption(f"Found {len(df_results)} lead(s)")
                for _, row in df_results.iterrows():
                    pk = int(row["pk"])
                    with st.expander(f"ID {row['ID']} — {row['Full Name']} ({row['Company Name']}) — currently: {row['Sales Person Name']}"):
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            new_sp = st.selectbox(
                                "Sales Person",
                                [""] + list(SALESPERSONS.values()),
                                index=(list(SALESPERSONS.values()).index(row["Sales Person Name"]) + 1)
                                if row["Sales Person Name"] in SALESPERSONS.values() else 0,
                                key=f"edit_sp_{pk}",
                            )
                            new_status = st.selectbox(
                                "Follow-up Status",
                                FOLLOWUP_STATUSES,
                                index=FOLLOWUP_STATUSES.index(row["Follow-up Status"])
                                if row["Follow-up Status"] in FOLLOWUP_STATUSES else 0,
                                key=f"edit_status_{pk}",
                            )
                        with ec2:
                            new_remarks = st.text_area(
                                "Remarks",
                                value=str(row["Remarks"]) if pd.notna(row["Remarks"]) else "",
                                key=f"edit_remarks_{pk}",
                            )

                        if st.button("Save", key=f"edit_save_{pk}", type="primary"):
                            updates = {}
                            if new_status != row["Follow-up Status"]:
                                updates["followup_status"] = new_status
                            if new_remarks != (str(row["Remarks"]) if pd.notna(row["Remarks"]) else ""):
                                updates["remarks"] = new_remarks if new_remarks else None
                            if new_sp and new_sp != row["Sales Person Name"]:
                                sp_email = [e for e, n in SALESPERSONS.items() if n == new_sp]
                                if sp_email:
                                    updates["sales_person"] = sp_email[0]
                                    updates["sales_person_name"] = new_sp
                                    for team, members in TEAMS.items():
                                        if new_sp in members:
                                            updates["sales_person_team"] = team
                                            break

                            if updates:
                                save_changes({pk: updates})
                                st.success("Saved!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.info("No changes detected.")

        # --- Bulk Reassign ---
        st.divider()
        st.markdown("#### Bulk Reassign")
        st.caption("Use this to reassign multiple leads at once (e.g., when a salesperson resigns).")

        ab1, ab2, ab3 = st.columns(3)
        with ab1:
            all_sp_for_bulk = sorted(df["Sales Person Name"].dropna().unique())
            all_sp_for_bulk = [n for n in all_sp_for_bulk if n.strip()]
            admin_bulk_from = st.multiselect(
                "From Salesperson", all_sp_for_bulk, default=[], placeholder="Select",
                key="admin_bulk_from"
            )
        with ab2:
            admin_bulk_status = st.multiselect(
                "Filter by Status", FOLLOWUP_STATUSES, default=[],
                placeholder="All statuses", key="admin_bulk_status"
            )
        with ab3:
            admin_bulk_team = st.multiselect(
                "Filter by Team", TEAM_ORDER + ["Unassigned"], default=[],
                placeholder="All teams", key="admin_bulk_team"
            )

        if admin_bulk_from or admin_bulk_status or admin_bulk_team:
            df_ab = df.copy()
            if admin_bulk_from:
                df_ab = df_ab[df_ab["Sales Person Name"].isin(admin_bulk_from)]
            if admin_bulk_status:
                df_ab = df_ab[df_ab["Follow-up Status"].isin(admin_bulk_status)]
            if admin_bulk_team:
                ab_members = []
                ab_unassigned = False
                for t in admin_bulk_team:
                    if t == "Unassigned":
                        ab_unassigned = True
                    else:
                        ab_members.extend(TEAMS.get(t, []))
                if ab_unassigned and ab_members:
                    df_ab = df_ab[(df_ab["Sales Person Name"].isin(ab_members)) | (df_ab["Sales Person Name"] == "")]
                elif ab_unassigned:
                    df_ab = df_ab[df_ab["Sales Person Name"] == ""]
                elif ab_members:
                    df_ab = df_ab[df_ab["Sales Person Name"].isin(ab_members)]

            ab_table = df_ab[["pk", "ID", "Full Name", "Company Name", "Contact Number",
                              "Sales Person Name", "Event Date Label", "Follow-up Status",
                              "Attendance"]].copy()
            ab_table.insert(0, "Select", False)

            st.caption(f"**{len(ab_table)}** leads match. Tick the ones to reassign, then click Reassign.")

            with st.form(key="admin_bulk_form"):
                edited_ab = st.data_editor(
                    ab_table,
                    column_config={
                        "pk": None,
                        "Select": st.column_config.CheckboxColumn("✓", width="small"),
                        "ID": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                        "Full Name": st.column_config.TextColumn("Name", disabled=True, width="medium"),
                        "Company Name": st.column_config.TextColumn("Company", disabled=True, width="medium"),
                        "Contact Number": st.column_config.TextColumn("Phone", disabled=True, width="small"),
                        "Sales Person Name": st.column_config.TextColumn("Current SP", disabled=True, width="small"),
                        "Event Date Label": st.column_config.TextColumn("Event", disabled=True, width="medium"),
                        "Follow-up Status": st.column_config.TextColumn("Status", disabled=True, width="small"),
                        "Attendance": st.column_config.NumberColumn("Attend", disabled=True, width="small"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    height=400,
                    key="admin_bulk_editor",
                )

                abc1, abc2 = st.columns(2)
                with abc1:
                    admin_bulk_target = st.selectbox(
                        "Reassign to", sorted(SALESPERSONS.values()), key="admin_bulk_target"
                    )
                with abc2:
                    admin_bulk_remark = st.checkbox(
                        "Append reassign remark", value=True, key="admin_bulk_remark"
                    )

                submitted_ab = st.form_submit_button("Reassign Selected Lead(s) Now", type="primary")

            if submitted_ab:
                ab_selected = edited_ab[edited_ab["Select"] == True]
                ab_count = len(ab_selected)

                if ab_count == 0:
                    st.warning("No leads selected.")
                else:
                    from datetime import datetime
                    now = datetime.now()
                    to_email = [e for e, n in SALESPERSONS.items() if n == admin_bulk_target][0]
                    to_team = ""
                    for team, members in TEAMS.items():
                        if admin_bulk_target in members:
                            to_team = team
                            break

                    changes = {}
                    for _, row in ab_selected.iterrows():
                        pk = int(row["pk"])
                        from_name = str(row["Sales Person Name"]).strip()
                        fs = str(row["Follow-up Status"]).strip()
                        updates = {
                            "sales_person": to_email,
                            "sales_person_name": admin_bulk_target,
                            "sales_person_team": to_team,
                        }
                        if admin_bulk_remark and from_name:
                            status_abbr = "UR" if fs == "Unreached" else fs
                            remark_suffix = f"reassign from {from_name.lower()}-{status_abbr} {now.day}/{now.month}"
                            supabase = get_supabase()
                            lead_resp = supabase.table("leads").select("remarks").eq("pk", pk).execute()
                            existing = (lead_resp.data[0].get("remarks") or "") if lead_resp.data else ""
                            updates["remarks"] = f"{existing}, {remark_suffix}".strip(", ") if existing else remark_suffix
                        changes[pk] = updates

                    with st.spinner(f"Reassigning {ab_count} leads..."):
                        save_changes(changes)
                    st.success(f"Done! {ab_count} lead(s) reassigned to {admin_bulk_target}.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Select a filter above to see leads for bulk reassignment.")

    # ==================================================================
    # TAB 3: CHARTS
    # ==================================================================
    with tab3:
        st.markdown("### Custom Status Analysis")
        st.caption("Select any combination of statuses to see the breakdown per salesperson")

        selected_statuses = st.multiselect(
            "Select statuses to analyse",
            FOLLOWUP_STATUSES,
            default=["Yet to call", "Unreached", "Follow Up", "Call Back"],
            key="chart_custom_status",
        )

        if selected_statuses:
            chart_team = st.multiselect(
                "Filter by Team", TEAM_ORDER, default=[], placeholder="All teams", key="chart_team"
            )

            df_chart = cascading_date_filter(df, "chart")

            if chart_team:
                chart_members = []
                for t in chart_team:
                    chart_members.extend(TEAMS.get(t, []))
                df_chart = df_chart[df_chart["Sales Person Name"].isin(chart_members)]

            df_custom = df_chart[df_chart["Follow-up Status"].isin(selected_statuses)]
            custom_counts = df_custom.groupby("Sales Person Name").size().reset_index(name="Count")
            custom_counts = custom_counts.sort_values("Count", ascending=True)

            total_in_group = custom_counts["Count"].sum()
            st.metric("Total leads in selected statuses", total_in_group)

            fig_custom = px.bar(
                custom_counts, x="Count", y="Sales Person Name", orientation="h",
                color="Count", color_continuous_scale="Reds",
                labels={"Sales Person Name": "Salesperson"}, text_auto=True,
            )
            fig_custom.update_traces(textposition="outside", textangle=0)
            fig_custom.update_layout(height=max(350, len(custom_counts) * 35), showlegend=False)
            st.plotly_chart(fig_custom, use_container_width=True)

            custom_detail = df_custom.groupby(
                ["Sales Person Name", "Follow-up Status"]
            ).size().reset_index(name="Count")
            fig_detail = px.bar(
                custom_detail, x="Sales Person Name", y="Count", color="Follow-up Status",
                barmode="stack", text_auto=True,
                labels={"Sales Person Name": "Salesperson"},
            )
            fig_detail.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_detail, use_container_width=True)

    # ==================================================================
    # TAB 4: DAILY REPORT
    # ==================================================================
    with tab4:
        st.markdown("### Daily Report — Team KPI Cards")
        st.caption("Screenshot-friendly summary for daily reporting")

        dr1, dr2 = st.columns(2)
        with dr1:
            target_pct = st.slider(
                "Calling Rate Target %", min_value=10, max_value=100, value=70, step=5,
                key="dr_target",
            )
        with dr2:
            dr_attendance = st.selectbox(
                "Attendance", ["All", "Attended (1)", "Not Attended (0)"], key="dr_attend"
            )

        df_report = cascading_date_filter(df, "dr")

        if dr_attendance == "Attended (1)":
            df_report = df_report[df_report["Attendance"] == 1]
        elif dr_attendance == "Not Attended (0)":
            df_report = df_report[df_report["Attendance"] == 0]

        st.divider()

        for team in TEAM_ORDER:
            members = TEAMS.get(team, [])
            df_team = df_report[df_report["Sales Person Name"].isin(members)]
            render_team_kpi_card(df_team, team, target_pct)

    # ==================================================================
    # TAB 5: UPLOAD NEW LEADS
    # ==================================================================
    with tab5:
        st.markdown("### Upload New Leads")
        st.caption("Upload a new Power App Excel download. Only new leads will be added (duplicates are skipped).")

        uploaded_file = st.file_uploader("Drag & drop your Excel file here", type=["xlsx", "xls"], key="upload_file")

        if uploaded_file:
            try:
                df_upload = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error(f"Could not read file: {e}")
                df_upload = None

            if df_upload is not None:
                # Check required columns
                required = ["ID", "Company Name", "Sales Person"]
                missing = [c for c in required if c not in df_upload.columns]
                if missing:
                    st.error(f"Missing required columns: {missing}")
                    st.info(f"Your file has: {list(df_upload.columns)}")
                else:
                    st.success(f"File loaded: **{len(df_upload)}** rows")

                    # Preview
                    with st.expander("Preview uploaded data"):
                        st.dataframe(df_upload.head(20), use_container_width=True, hide_index=True)

                    # Find duplicates
                    existing_keys = set()
                    for _, row in df_full.iterrows():
                        key = f"{row['ID']}|{str(row.get('Company Name', '')).strip().lower()}"
                        existing_keys.add(key)

                    new_rows = []
                    for _, row in df_upload.iterrows():
                        id_val = str(row.get("ID", "")).strip()
                        company = str(row.get("Company Name", "")).strip().lower()
                        key = f"{id_val}|{company}"
                        if key not in existing_keys:
                            new_rows.append(row)

                    dupe_count = len(df_upload) - len(new_rows)

                    st.markdown(f"""
                    | | Count |
                    |---|---|
                    | Total rows in file | **{len(df_upload)}** |
                    | Duplicates (will be skipped) | **{dupe_count}** |
                    | **New leads to add** | **{len(new_rows)}** |
                    """)

                    if len(new_rows) == 0:
                        st.info("All rows already exist in the database. Nothing to import.")
                    else:
                        if st.button(f"Import {len(new_rows)} new leads", type="primary", key="import_btn"):
                            with st.spinner(f"Importing {len(new_rows)} leads..."):
                                import numpy as np

                                COLUMN_MAP = {
                                    "ID": "id", "Full Name": "full_name", "Company Name": "company_name",
                                    "Contact Number": "contact_number", "Email Address": "email_address",
                                    "Designation": "designation", "Sales Person": "sales_person",
                                    "Reminder Call PIC": "reminder_call_pic", "Concern": "concern",
                                    "Leads": "leads", "utm_source": "utm_source", "utm_medium": "utm_medium",
                                    "utm_campaign": "utm_campaign", "utm_term": "utm_term",
                                    "utm_content": "utm_content", "Area": "area", "Revenue (M)": "revenue_m",
                                    "HRDC": "hrdc", "Reference Link": "reference_link", "Industry": "industry",
                                    "Created": "created_at", "Zoom Link": "zoom_link",
                                    "Confirmation Status": "confirmation_status",
                                    "Reminder Call Status": "reminder_call_status",
                                    "Follow-up Status": "followup_status",
                                    "Conversation Log": "conversation_log", "Attendance": "attendance",
                                    "Preview Date": "preview_date", "Sales Person Name": "sales_person_name",
                                    "Sales Person Team": "sales_person_team", "UTM Value": "utm_value",
                                    "UTM Grouping": "utm_grouping", "Topic": "topic", "Remarks": "remarks",
                                    "Duplicate Check": "duplicate_check", "Registered": "registered",
                                    "Attended": "attended",
                                }
                                INT_COLS = ("id", "attendance", "registered")
                                BOOL_COLS = ("leads", "hrdc")
                                FLOAT_COLS = ("revenue_m", "attended")

                                def _clean(val):
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

                                records = []
                                for row_data in new_rows:
                                    record = {}
                                    for excel_col, db_col in COLUMN_MAP.items():
                                        val = row_data.get(excel_col)
                                        if excel_col == "Contact Number":
                                            if val is None or (isinstance(val, float) and np.isnan(val)):
                                                val = None
                                            elif isinstance(val, (int, np.integer)):
                                                val = str(val)
                                            elif isinstance(val, float):
                                                val = str(int(val))
                                            else:
                                                val = str(val).strip() if str(val).strip() not in ("", "nan") else None
                                        else:
                                            val = _clean(val)

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

                                    # Auto-fill name & team
                                    if not record.get("sales_person_name") and record.get("sales_person"):
                                        email = record["sales_person"].lower()
                                        name_map = {k.lower(): v for k, v in SALESPERSONS.items()}
                                        record["sales_person_name"] = name_map.get(email, "")
                                    if not record.get("sales_person_team") and record.get("sales_person_name"):
                                        for t, m in TEAMS.items():
                                            if record["sales_person_name"] in m:
                                                record["sales_person_team"] = t
                                                break
                                    if not record.get("followup_status"):
                                        record["followup_status"] = "Yet to call"

                                    records.append(record)

                                # Insert in batches
                                supabase = get_supabase()
                                batch_size = 500
                                for i in range(0, len(records), batch_size):
                                    batch = records[i : i + batch_size]
                                    supabase.table("leads").insert(batch).execute()

                                load_data.clear()
                                st.success(f"Done! **{len(records)}** new leads imported.")
                                time.sleep(2)
                                st.rerun()

    # ==================================================================
    # TAB 6: REASSIGN REQUESTS
    # ==================================================================
    with tab6:
        st.markdown("### Pending Requests")

        if not pending_reassign:
            st.info("No pending reassign requests.")
        else:
            for req in pending_reassign:
                with st.expander(
                    f"📌 {req['lead_name']} ({req['lead_company']}) — "
                    f"{req['from_sp_name']} → {req['to_sp_name']}"
                ):
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.markdown(f"**Lead:** {req['lead_name']}")
                        st.markdown(f"**Company:** {req['lead_company']}")
                        st.markdown(f"**Current Status:** {req['current_followup_status']}")
                    with rc2:
                        st.markdown(f"**From:** {req['from_sp_name']}")
                        st.markdown(f"**To:** {req['to_sp_name']}")
                        st.markdown(f"**Submitted:** {str(req['created_at'])[:16]}")
                    st.markdown(f"**Reason:** {req['reason']}")

                    rj_reason = st.text_input(
                        "Reject reason (optional)", "", key=f"rj_reason_{req['id']}"
                    )

                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("✅ Approve", key=f"approve_{req['id']}", type="primary"):
                            ok, msg = process_reassign_request(req["id"], "Approved")
                            if ok:
                                st.success(msg)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(msg)
                    with bc2:
                        if st.button("❌ Reject", key=f"reject_{req['id']}"):
                            ok, msg = process_reassign_request(
                                req["id"], "Rejected", reject_reason=rj_reason
                            )
                            if ok:
                                st.success(msg)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(msg)

        st.divider()
        st.markdown("### History")
        all_requests = load_reassign_requests()
        history = [r for r in all_requests if r["status"] != "Pending"]
        if history:
            hist_df = pd.DataFrame(history)
            hist_display = hist_df[[
                "lead_name", "lead_company", "from_sp_name", "to_sp_name",
                "reason", "status", "reject_reason", "current_followup_status",
                "created_at", "reviewed_at",
            ]].copy()
            hist_display.columns = [
                "Lead", "Company", "From", "To", "Reason", "Status",
                "Reject Reason", "Follow-up Status", "Submitted", "Reviewed",
            ]
            hist_display["Submitted"] = hist_display["Submitted"].astype(str).str[:16]
            hist_display["Reviewed"] = hist_display["Reviewed"].astype(str).str[:16]
            hist_display["Reject Reason"] = hist_display["Reject Reason"].fillna("")
            st.dataframe(hist_display, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No history yet.")


# ==============================================================================
# MAIN
# ==============================================================================


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Supabase configuration missing.")
        st.info("Add SUPABASE_URL and SUPABASE_KEY to your Streamlit secrets.")
        st.stop()

    if "user_email" not in st.session_state:
        login_page()
        return

    # Keep session alive — ping every 2 minutes to prevent idle timeout
    components.html(
        """<script>
        setInterval(function() {
            fetch(window.location.href, {method: 'HEAD', cache: 'no-store'});
        }, 120000);
        </script>""",
        height=0,
    )

    user_email = st.session_state["user_email"]
    user_name = st.session_state["user_name"]
    is_admin = st.session_state.get("is_admin", False)
    is_manager = st.session_state.get("is_manager", False)

    with st.sidebar:
        st.markdown(f"**{user_name}**")
        if is_admin:
            st.caption("Admin")
        elif is_manager:
            st.caption(f"Manager — {st.session_state.get('manager_team', '')}")
        else:
            st.caption("Salesperson")
        if st.button("Logout", use_container_width=True):
            for key in ["user_email", "user_name", "is_admin", "is_manager", "manager_team"]:
                st.session_state.pop(key, None)
            st.rerun()

    if is_admin:
        admin_view()
    elif is_manager:
        manager_view(user_email, user_name, st.session_state["manager_team"])
    else:
        salesperson_view(user_email, user_name)


if __name__ == "__main__":
    main()
