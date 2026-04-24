import html as html_lib
import json
import os
import re
import requests
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import plotly.express as px
import streamlit as st

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Team Dashboard | Aon",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── AON Brand Colours ─────────────────────────────────────────────────────────
AON_RED       = "#C8102E"
AON_BLACK     = "#1A1A1A"
AON_WHITE     = "#FFFFFF"
AON_GRAY_100  = "#F5F5F5"
AON_GRAY_200  = "#E8E8E8"
AON_GRAY_400  = "#AAAAAA"
AON_GRAY_600  = "#666666"

SIDEBAR_BG = "#0D1B2E"   # Deep professional navy
HEADER_BG  = "#FFFFFF"   # Clean white header

# ── Theme injection ───────────────────────────────────────────────────────────
def inject_css() -> str:
    """Inject AON-branded CSS and return the Plotly template name."""
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * {{ font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important; }}

    [data-testid="stAppViewContainer"] {{
        background-color: {AON_WHITE} !important;
        color: {AON_BLACK};
    }}
    [data-testid="stMain"] {{ background-color: {AON_WHITE} !important; }}

    [data-testid="stHeader"] {{
        background-color: {HEADER_BG} !important;
        border-bottom: 3px solid {AON_RED} !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: {SIDEBAR_BG} !important;
        border-right: 3px solid {AON_RED};
    }}
    [data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
    [data-testid="stSidebar"] label p {{
        color: {AON_GRAY_400} !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    [data-testid="stSidebar"] hr {{ border-color: #1F3550 !important; }}
    [data-testid="stSidebar"] [data-baseweb="select"] > div {{
        background-color: #162840 !important;
        border-color: #2A3F5A !important;
    }}

    /* Date input text box — dark text on light background so selected range is readable */
    [data-testid="stSidebar"] [data-baseweb="input"] input,
    [data-testid="stSidebar"] [data-baseweb="input"] {{
        color: {AON_BLACK} !important;
        background-color: #F0F4F8 !important;
        border-color: #2A3F5A !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="input"] input::placeholder {{
        color: #888 !important;
    }}

    /* Hide sidebar collapse button (shows raw icon name on hover) */
    [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}

    [data-testid="metric-container"] {{
        background-color: {AON_WHITE};
        border: 1px solid {AON_GRAY_200};
        border-top: 3px solid {AON_RED};
        border-radius: 4px;
        padding: 14px 18px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }}
    [data-testid="metric-container"] label {{
        color: {AON_GRAY_600} !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600;
    }}
    [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {AON_RED} !important;
        font-size: 1.9rem !important;
        font-weight: 700 !important;
    }}

    .aon-section-title {{
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: {AON_RED};
        margin-bottom: 6px;
    }}

    hr {{ border-color: {AON_GRAY_200} !important; }}

    [data-testid="stProgress"] > div > div > div > div {{
        background-color: {AON_RED} !important;
    }}
    [data-testid="stProgress"] > div > div > div {{
        background-color: {AON_GRAY_200} !important;
        border-radius: 2px;
    }}

    [data-testid="stDataFrame"] {{
        border: 1px solid {AON_GRAY_200};
        border-radius: 4px;
    }}

    [data-testid="stTextInput"] input:focus {{
        border-color: {AON_RED} !important;
        box-shadow: 0 0 0 2px rgba(200,16,46,0.18) !important;
    }}

    [data-testid="stCaptionContainer"] p {{
        color: {AON_GRAY_600} !important;
        font-size: 0.78rem;
    }}

    [data-testid="stInfoMessage"] {{
        background-color: {AON_GRAY_100};
        border-left-color: {AON_RED};
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    return "plotly_white"


plotly_template = inject_css()


# ── AON chart layout helper ───────────────────────────────────────────────────
def aon_layout(fig, height: int = 320):
    fig.update_layout(
        height=height,
        margin=dict(t=10, b=10, l=0, r=0),
        plot_bgcolor=AON_WHITE,
        paper_bgcolor=AON_WHITE,
        font=dict(family="Inter, Segoe UI, Arial, sans-serif",
                  color=AON_BLACK, size=11),
        xaxis=dict(gridcolor=AON_GRAY_200, linecolor=AON_GRAY_200),
        yaxis=dict(gridcolor=AON_GRAY_200, linecolor=AON_GRAY_200),
        legend=dict(font=dict(size=10)),
    )
    return fig


# ── Colour maps ───────────────────────────────────────────────────────────────
STATE_COLORS = {
    "To Do":       "#AAAAAA",
    "In Progress": "#1B75BC",
    "In Review":   "#E87722",
    "Blocked":     "#C8102E",
    "Done":        "#2D8653",
}
PRIORITY_COLORS = {
    "Critical": "#C8102E",
    "High":     "#E87722",
    "Medium":   "#F5C518",
    "Low":      "#2D8653",
}
PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]

AON_CHART_SEQ = [
    "#C8102E", "#A00E24", "#E8485A",
    "#1B75BC", "#E87722", "#2D8653", "#6C3483",
]

# ── Azure DevOps configuration ────────────────────────────────────────────────
AZURE_ORG        = os.environ.get("AZURE_DEVOPS_ORG",     "aononedevops")
AZURE_PROJECT    = os.environ.get("AZURE_DEVOPS_PROJECT", "ACIA_Health_Solutions_App")
AZURE_QUERY_NAME = os.environ.get("AZURE_DEVOPS_QUERY",   "")   # set via env var
AZURE_PAT        = os.environ.get("AZURE_DEVOPS_PAT",     "")

# Azure DevOps state → dashboard state mapping
AZURE_STATE_MAP = {
    "new": "To Do", "proposed": "To Do", "to do": "To Do",
    "active": "In Progress", "in progress": "In Progress", "committed": "In Progress",
    "in review": "In Review", "in testing": "In Review",
    "blocked": "Blocked", "on hold": "Blocked",
    "done": "Done", "closed": "Done", "resolved": "Done", "completed": "Done",
}

# ── Role mapping (hardcoded — update with your team members' actual roles) ────
MEMBER_ROLES: dict[str, str] = {
    # "Full Name As In Azure DevOps": "Role Title",
    # Example:
    # "Alice Johnson": "Senior QA Engineer",
    # "Bob Smith":     "QA Engineer",
}

# ── Azure DevOps data fetch ───────────────────────────────────────────────────
def fetch_and_save_azure_data() -> tuple[bool, str]:
    """Fetch tasks from Azure DevOps via saved query and overwrite sample_data.json.

    Returns (success: bool, message: str).
    """
    if not AZURE_PAT:
        return False, "AZURE_DEVOPS_PAT environment variable is not set."
    if not AZURE_QUERY_NAME:
        return False, "AZURE_DEVOPS_QUERY environment variable is not set."

    auth = ("", AZURE_PAT)
    base = f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}"

    # Step 1 – find saved query ID by name
    try:
        resp = requests.get(
            f"{base}/_apis/wit/queries?$depth=2&$expand=all&api-version=7.0",
            auth=auth, timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return False, f"Failed to reach Azure DevOps: {exc}"

    def _find_query(node: dict) -> str | None:
        if node.get("name") == AZURE_QUERY_NAME:
            return node["id"]
        for child in node.get("children", []) + node.get("value", []):
            found = _find_query(child)
            if found:
                return found
        return None

    query_id = _find_query(resp.json())
    if not query_id:
        return False, f"Query '{AZURE_QUERY_NAME}' not found in Azure DevOps."

    # Step 2 – run the query to get work item IDs
    try:
        resp = requests.get(
            f"{base}/_apis/wit/wiql/{query_id}?api-version=7.0",
            auth=auth, timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return False, f"Failed to execute query: {exc}"

    work_item_refs = resp.json().get("workItems", [])
    if not work_item_refs:
        return False, "Query returned no work items."

    ids = [item["id"] for item in work_item_refs]

    # Step 3 – fetch work item details in batches of 200
    fields = ",".join([
        "System.Id", "System.Title", "System.State", "System.AssignedTo",
        "System.TeamProject", "System.AreaPath", "System.IterationPath",
        "System.Description", "Microsoft.VSTS.Common.Priority",
        "System.WorkItemType", "System.CreatedDate", "System.ChangedDate",
    ])
    all_items: list[dict] = []
    try:
        for i in range(0, len(ids), 200):
            batch = ids[i : i + 200]
            ids_str = ",".join(str(wid) for wid in batch)
            resp = requests.get(
                f"{base}/_apis/wit/workitems?ids={ids_str}&fields={fields}&api-version=7.0",
                auth=auth, timeout=30,
            )
            resp.raise_for_status()
            all_items.extend(resp.json().get("value", []))
    except requests.RequestException as exc:
        return False, f"Failed to fetch work item details: {exc}"

    # Step 4 – transform and group by assigned team member
    members_map: dict[str, dict] = {}
    for item in all_items:
        f = item.get("fields", {})

        assigned_raw = f.get("System.AssignedTo", {})
        member_name = (
            assigned_raw.get("displayName", "Unassigned")
            if isinstance(assigned_raw, dict)
            else (str(assigned_raw) if assigned_raw else "Unassigned")
        )

        project_name = f.get("System.TeamProject", AZURE_PROJECT)
        project_id   = "".join(w[0].upper() for w in project_name.split() if w)

        raw_state = f.get("System.State", "To Do")
        state     = AZURE_STATE_MAP.get(raw_state.lower(), raw_state)

        raw_priority = f.get("Microsoft.VSTS.Common.Priority")
        priority     = int(raw_priority) if raw_priority is not None else 3

        created = (f.get("System.CreatedDate") or "")[:10]
        updated = (f.get("System.ChangedDate") or "")[:10]

        # Strip HTML tags from description
        raw_desc    = f.get("System.Description") or ""
        description = re.sub(r"<[^>]+>", " ", raw_desc).strip()

        task = {
            "id":           str(f.get("System.Id", "")),
            "summary":      f.get("System.Title", ""),
            "assigned_to":  member_name,
            "state":        state,
            "area":         f.get("System.AreaPath", ""),
            "iteration":    f.get("System.IterationPath", ""),
            "description":  description,
            "priority":     priority,
            "task_type":    f.get("System.WorkItemType", "Task"),
            "created_date": created,
            "updated_date": updated,
        }

        if member_name not in members_map:
            members_map[member_name] = {
                "id":         f"TM{len(members_map) + 1:03d}",
                "name":       member_name,
                "role":       MEMBER_ROLES.get(member_name, "QA Engineer"),
                "project":    project_name,
                "project_id": project_id,
                "tasks":      [],
            }
        members_map[member_name]["tasks"].append(task)

    # Step 5 – persist to sample_data.json
    data = {"team_members": list(members_map.values())}
    _DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return True, f"Fetched {len(all_items)} task(s) for {len(members_map)} team member(s)."


# ── Data loading ──────────────────────────────────────────────────────────────
_DATA_FILE = Path(__file__).parent / "sample_data.json"


@st.cache_data
def load_data() -> pd.DataFrame:
    if not _DATA_FILE.exists():
        st.error(f"Data file not found: {_DATA_FILE}")
        st.stop()
    try:
        raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON in data file: {exc}")
        st.stop()

    rows = []
    for member in raw["team_members"]:
        for task in member["tasks"]:
            rows.append(
                {
                    **task,
                    "member_name": member["name"],
                    "project":     member["project"],
                    "role":        member["role"],
                }
            )

    df = pd.DataFrame(rows)
    df["created_date"] = pd.to_datetime(df["created_date"])
    df["updated_date"] = pd.to_datetime(df["updated_date"])
    df["priority_label"] = df["priority"].map(
        {1: "Critical", 2: "High", 3: "Medium", 4: "Low"}
    )
    return df


df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="aon-section-title">Filters</p>', unsafe_allow_html=True)

    all_members = sorted(df["member_name"].unique().tolist())
    sel_members = st.multiselect("Team Member", all_members, default=all_members)

    all_projects = sorted(df["project"].unique().tolist())
    sel_projects = st.multiselect("Project", all_projects, default=all_projects)

    state_options = ["To Do", "In Progress", "In Review", "Blocked", "Done"]
    sel_states = st.multiselect("State", state_options, default=state_options)

    sel_priorities = st.multiselect("Priority", PRIORITY_ORDER, default=PRIORITY_ORDER)

    all_task_types = sorted(df["task_type"].unique().tolist())
    sel_task_types = st.multiselect("Task Type", all_task_types, default=all_task_types)

    st.divider()
    st.markdown(
        f'<p style="font-size:0.68rem; color:#666; text-align:center;">'
        f'© {date.today().year} Aon plc. All rights reserved.</p>',
        unsafe_allow_html=True,
    )

# ── Apply sidebar filters (date applied after header widget) ──────────────────
fdf = df[
    df["member_name"].isin(sel_members)
    & df["project"].isin(sel_projects)
    & df["state"].isin(sel_states)
    & df["priority_label"].isin(sel_priorities)
    & df["task_type"].isin(sel_task_types)
].copy()

# ── Page header with inline Date Range picker ─────────────────────────────────
min_d = df["created_date"].min().date()
max_d = df["created_date"].max().date()

col_logo, col_title, col_date = st.columns([1, 5, 3])
with col_logo:
    st.markdown(
        '<div style="font-size:2.6rem; font-weight:900; color:#C8102E; '
        'letter-spacing:0.04em; line-height:1; padding-top:4px;">AON</div>',
        unsafe_allow_html=True,
    )
with col_title:
    st.markdown(
        """
        <div style="border-left:3px solid #C8102E; padding-left:14px;">
            <div style="font-size:1.35rem; font-weight:700; line-height:1.2;">
                QA Team Dashboard
            </div>
            <div style="font-size:0.78rem; color:#888; margin-top:3px;">
                Test Lead &nbsp;·&nbsp; Work Status Overview &nbsp;·&nbsp; Azure DevOps
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_date:
    _, refresh_btn_col = st.columns([1, 1])
    with refresh_btn_col:
        if st.button("🔄 Refresh Data", use_container_width=True):
            with st.spinner("Fetching data from Azure DevOps…"):
                ok, msg = fetch_and_save_azure_data()
            if ok:
                st.success(msg)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(msg)
    date_range = st.date_input(
        "Date Range",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
    )

# Apply date filter
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    fdf = fdf[
        (fdf["created_date"].dt.date >= date_range[0])
        & (fdf["created_date"].dt.date <= date_range[1])
    ]
elif isinstance(date_range, date):
    st.warning("Select an end date to complete the date range filter.")
    fdf = fdf[fdf["created_date"].dt.date >= date_range]

st.markdown(
    f'<p style="font-size:0.78rem; color:#888; margin-top:8px;">'
    f'Showing <strong>{len(fdf)}</strong> task(s) across '
    f'<strong>{len(sel_members)}</strong> member(s) &nbsp;·&nbsp; '
    f'{date.today().strftime("%B %d, %Y")}</p>',
    unsafe_allow_html=True,
)
st.divider()

# ── KPI metric cards ──────────────────────────────────────────────────────────
state_counts = fdf["state"].value_counts()
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Tasks",  len(fdf))
k2.metric("In Progress",  int(state_counts.get("In Progress", 0)))
k3.metric("Done",         int(state_counts.get("Done",        0)))
k4.metric("Blocked",      int(state_counts.get("Blocked",     0)))
k5.metric("To Do",        int(state_counts.get("To Do",       0)))
k6.metric("In Review",    int(state_counts.get("In Review",   0)))

st.divider()

# ── Team Summary Table ────────────────────────────────────────────────────────
st.markdown('<p class="aon-section-title">Team Summary</p>', unsafe_allow_html=True)

if not fdf.empty:
    state_order = ["To Do", "In Progress", "In Review", "Blocked", "Done"]
    pivot = (
        fdf.groupby(["member_name", "state"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=[s for s in state_order if s in fdf["state"].unique()], fill_value=0)
    )
    pivot.index.name = "Team Member"
    pivot["Total"] = pivot.sum(axis=1)
    pivot["% Done"] = (pivot.get("Done", 0) / pivot["Total"] * 100).round(1).astype(str) + "%"
    pivot = pivot.reset_index()

    st.dataframe(
        pivot,
        width="stretch",
        hide_index=True,
        column_config={
            "Team Member": st.column_config.TextColumn(width="medium"),
            "To Do":       st.column_config.NumberColumn(width="small"),
            "In Progress": st.column_config.NumberColumn(width="small"),
            "In Review":   st.column_config.NumberColumn(width="small"),
            "Blocked":     st.column_config.NumberColumn(width="small"),
            "Done":        st.column_config.NumberColumn(width="small"),
            "Total":       st.column_config.NumberColumn(width="small"),
            "% Done":      st.column_config.TextColumn(width="small"),
        },
    )
else:
    st.info("No data for selected filters.")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
st.markdown('<p class="aon-section-title">Status Overview</p>', unsafe_allow_html=True)

ch_left, ch_right = st.columns([1, 1])

with ch_left:
    st.markdown("**Task Type Breakdown**")
    if not fdf.empty:
        tc = fdf["task_type"].value_counts().reset_index()
        tc.columns = ["Task Type", "Count"]
        total_tasks = tc["Count"].sum()
        tc["Percentage"] = (tc["Count"] / total_tasks * 100).round(1)

        # Build per-task-type done/remaining counts and task-level ID+state lines
        def _task_lines(grp):
            STATE_ICON = {
                "Done": "✔",
                "In Progress": "▶",
                "In Review": "◎",
                "Blocked": "✖",
                "To Do": "○",
            }
            STATE_ORDER = {"Done": 0, "In Progress": 1, "In Review": 2, "Blocked": 3, "To Do": 4}
            sorted_grp = grp.assign(_ord=grp["state"].map(STATE_ORDER).fillna(5)).sort_values("_ord")
            lines = []
            for _, row in sorted_grp.iterrows():
                icon = STATE_ICON.get(row["state"], "·")
                summary = row["summary"][:55] + "…" if len(row["summary"]) > 55 else row["summary"]
                lines.append(
                    f"{icon} <b>{row['id']}</b>  [{row['state']}]<br>"
                    f"&nbsp;&nbsp;&nbsp;{summary}<br>"
                    f"&nbsp;&nbsp;&nbsp;👤 {row['member_name']}  &nbsp;·&nbsp; 📁 {row['project']}"
                )
            return "<br>".join(lines)

        type_detail = (
            fdf.groupby("task_type")
            .apply(lambda g: pd.Series({
                "Done":      int((g["state"] == "Done").sum()),
                "Remaining": int((g["state"] != "Done").sum()),
                "task_lines": _task_lines(g),
            }), include_groups=False)
            .reset_index()
            .rename(columns={"task_type": "Task Type"})
        )
        tc = tc.merge(type_detail, on="Task Type")

        TREEMAP_COLORS = [
            "#0D1B2E", "#1B75BC", "#2D8653", "#E87722",
            "#6C3483", "#C8102E", "#17A589", "#E8A838",
        ]

        fig = px.treemap(
            tc,
            path=["Task Type"],
            values="Count",
            color="Task Type",
            color_discrete_sequence=TREEMAP_COLORS,
            template=plotly_template,
            custom_data=["Count", "Percentage", "Done", "Remaining", "task_lines"],
        )
        fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{customdata[0]}<br>(%{customdata[1]}%)",
            textfont=dict(size=13, color="white"),
            textposition="middle center",
            marker=dict(line=dict(width=2, color=AON_WHITE)),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "<span style='font-size:11px;'>%{customdata[0]} task(s) &nbsp;·&nbsp; %{customdata[1]}% of total</span><br>"
                "──────────────────────<br>"
                "<span style='color:#5B9A78;'>✔ Done: %{customdata[2]}</span> &nbsp;|&nbsp; "
                "<span style='color:#E87722;'>Remaining: %{customdata[3]}</span><br>"
                "──────────────────────<br>"
                "%{customdata[4]}"
                "<extra></extra>"
            ),
            hoverlabel=dict(
                bgcolor="#1A1A1A", bordercolor="#C8102E",
                font=dict(family="Inter, Segoe UI, Arial, sans-serif",
                          size=12, color="#FFFFFF"),
                align="left",
            ),
        )
        fig = aon_layout(fig, height=300)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No data for selected filters.")

with ch_right:
    st.markdown("**Status by Team Member**")
    if not fdf.empty:
        # Build a per-(member, state) task list for the hover tooltip
        _tmp = fdf.copy()
        _tmp["task_line"] = (
            _tmp["id"].astype(str)
            + " — "
            + _tmp["summary"].str[:60].where(
                _tmp["summary"].str.len() <= 60,
                _tmp["summary"].str[:60] + "…",
            )
        )
        task_details = (
            _tmp.groupby(["member_name", "state"])["task_line"]
            .apply(lambda lines: "<br>".join(lines))
            .reset_index(name="task_list")
        )

        ms = (
            fdf.groupby(["member_name", "state"])
            .size()
            .reset_index(name="Count")
        )
        ms = ms.merge(task_details, on=["member_name", "state"])
        ms["label"] = ms["member_name"].str.split().str[0]

        MUTED_STATE = {
            "To Do":       "#BDBDBD",
            "In Progress": "#5B8DB8",
            "In Review":   "#C8956C",
            "Blocked":     "#B85C5C",
            "Done":        "#5B9A78",
        }
        fig = px.bar(
            ms, x="label", y="Count", color="state",
            barmode="stack", color_discrete_map=MUTED_STATE,
            template=plotly_template,
            custom_data=["member_name", "state", "Count", "task_list"],
        )
        fig.update_traces(
            hovertemplate=(
                "<span style='font-size:13px; font-weight:700;'>"
                "%{customdata[0]}</span>"
                "<br>"
                "<span style='font-size:11px; color:#888;'>%{customdata[1]}"
                " &nbsp;·&nbsp; %{customdata[2]} task(s)</span>"
                "<br><br>"
                "%{customdata[3]}"
                "<extra></extra>"
            ),
            hoverlabel=dict(
                bgcolor="#1A1A1A",
                bordercolor="#C8102E",
                font=dict(family="Inter, Segoe UI, Arial, sans-serif",
                          size=12, color="#FFFFFF"),
            ),
        )
        fig = aon_layout(fig, height=300)
        fig.update_layout(
            xaxis_title="", yaxis_title="Tasks",
            legend_title="State",
            legend=dict(orientation="v", font=dict(size=10)),
            bargap=0.35,
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No data for selected filters.")

st.divider()

# ── Per-member progress cards ─────────────────────────────────────────────────
st.markdown('<p class="aon-section-title">Team Member Progress</p>',
            unsafe_allow_html=True)

if sel_members:
    card_cols = st.columns(3)
    for idx, member in enumerate(sel_members):
        mdf = fdf[fdf["member_name"] == member]
        total_m   = len(mdf)
        done_m    = int((mdf["state"] == "Done").sum())
        prog_m    = int((mdf["state"] == "In Progress").sum())
        blocked_m = int((mdf["state"] == "Blocked").sum())
        review_m  = int((mdf["state"] == "In Review").sum())
        todo_m    = int((mdf["state"] == "To Do").sum())
        project_m = mdf["project"].iloc[0] if total_m > 0 else "N/A"
        role_m    = mdf["role"].iloc[0]    if total_m > 0 else ""
        pct       = done_m / total_m if total_m > 0 else 0.0

        card_text_col = AON_BLACK
        card_meta_col = AON_GRAY_600
        card_bg_col   = AON_WHITE
        card_brd_col  = AON_GRAY_200

        with card_cols[idx % 3]:
            member_esc  = html_lib.escape(member)
            project_esc = html_lib.escape(project_m)
            role_esc    = html_lib.escape(role_m)
            st.markdown(
                f"""
                <div style="
                    background:{card_bg_col};
                    border:1px solid {card_brd_col};
                    border-left:4px solid {AON_RED};
                    border-radius:4px;
                    padding:16px 18px 10px 18px;
                    margin-bottom:6px;
                    box-shadow:0 1px 4px rgba(0,0,0,0.07);
                ">
                    <div style="font-size:1rem; font-weight:700;
                                color:{card_text_col}; margin-bottom:2px;">
                        {member_esc}
                    </div>
                    <div style="font-size:0.76rem; color:{card_meta_col};
                                margin-bottom:10px;">
                        {project_esc} &nbsp;·&nbsp; {role_esc}
                    </div>
                    <div style="display:flex; gap:12px; flex-wrap:wrap;">
                        <span style="font-size:0.78rem;">
                            <strong style="color:{STATE_COLORS['In Progress']};">{prog_m}</strong>
                            <span style="color:{card_meta_col};"> In Progress</span>
                        </span>
                        <span style="font-size:0.78rem;">
                            <strong style="color:{STATE_COLORS['Done']};">{done_m}</strong>
                            <span style="color:{card_meta_col};"> Done</span>
                        </span>
                        <span style="font-size:0.78rem;">
                            <strong style="color:{AON_RED};">{blocked_m}</strong>
                            <span style="color:{card_meta_col};"> Blocked</span>
                        </span>
                        <span style="font-size:0.78rem;">
                            <strong style="color:{STATE_COLORS['In Review']};">{review_m}</strong>
                            <span style="color:{card_meta_col};"> In Review</span>
                        </span>
                        <span style="font-size:0.78rem;">
                            <strong style="color:{card_text_col};">{todo_m}</strong>
                            <span style="color:{card_meta_col};"> To Do</span>
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.progress(pct, text=f"Done: **{done_m}/{total_m}** ({pct*100:.0f}%)")
            st.write("")
else:
    st.info("Select at least one team member from the sidebar.")

st.divider()

# ── Task list ─────────────────────────────────────────────────────────────────
st.markdown('<p class="aon-section-title">Task List</p>', unsafe_allow_html=True)

search = st.text_input(
    "Search tasks",
    placeholder="Search by summary or description keyword…",
)

display = fdf.copy()
if search.strip():
    mask = (
        display["summary"].str.contains(search.strip(), case=False, na=False, regex=False)
        | display["description"].str.contains(search.strip(), case=False, na=False, regex=False)
    )
    display = display[mask]

col_sort, col_order = st.columns([3, 1])
with col_sort:
    sort_by = st.selectbox(
        "Sort by",
        ["created_date", "updated_date", "priority", "state",
         "member_name", "task_type", "project"],
        format_func=lambda x: {
            "created_date": "Created Date",
            "updated_date": "Updated Date",
            "priority":     "Priority",
            "state":        "State",
            "member_name":  "Assigned To",
            "task_type":    "Task Type",
            "project":      "Project",
        }[x],
    )
with col_order:
    order_choice = st.selectbox("Order", ["Descending ↓", "Ascending ↑"])
    ascending = order_choice == "Ascending ↑"

display = display.sort_values(sort_by, ascending=ascending)

display_clean = display[
    ["id", "summary", "member_name", "project", "state",
     "priority_label", "task_type", "area", "iteration",
     "created_date", "updated_date"]
].copy()
display_clean["created_date"] = display_clean["created_date"].dt.strftime("%Y-%m-%d")
display_clean["updated_date"] = display_clean["updated_date"].dt.strftime("%Y-%m-%d")
display_clean = display_clean.rename(
    columns={
        "id":             "ID",
        "summary":        "Summary",
        "member_name":    "Assigned To",
        "project":        "Project",
        "state":          "State",
        "priority_label": "Priority",
        "task_type":      "Task Type",
        "area":           "Area",
        "iteration":      "Iteration",
        "created_date":   "Created",
        "updated_date":   "Updated",
    }
)

st.dataframe(
    display_clean,
    width="stretch",
    hide_index=True,
    column_config={
        "ID":       st.column_config.TextColumn(width="small"),
        "Summary":  st.column_config.TextColumn(width="large"),
        "State":    st.column_config.TextColumn(width="small"),
        "Priority": st.column_config.TextColumn(width="small"),
        "Created":  st.column_config.TextColumn(width="small"),
        "Updated":  st.column_config.TextColumn(width="small"),
    },
)
st.caption(
    f"Showing **{len(display)}** task(s)  ·  {len(fdf)} total after sidebar filters"
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"""
    <div style="display:flex; justify-content:space-between; align-items:center;
                padding:8px 0; font-size:0.72rem; color:#888;">
        <span>
            <strong style="color:{AON_RED};">AON</strong> &nbsp;QA Team Dashboard
            &nbsp;·&nbsp; Sample Data Mode
            &nbsp;·&nbsp; Connect Azure DevOps API for live data
        </span>
        <span>© {date.today().year} Aon plc. All rights reserved.</span>
    </div>
    """,
    unsafe_allow_html=True,
)
