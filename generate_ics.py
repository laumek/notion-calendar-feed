import requests
from ics import Calendar, Event
from collections import defaultdict
import os
import re
from datetime import datetime

# --- CONFIG ---
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")
CUTOFF_DATE = datetime(2025, 7, 1)  # Only tasks on/after this date

# --- HELPERS ---
def clean_text(s):
    """Remove emojis, links, and special characters from text."""
    return re.sub(r"[^\w\s-]", "", s)

def create_vtodo(uid, summary, due_date, timed=False, start_date=None, end_date=None):
    """Return a string representing a VTODO ICS entry."""
    lines = [
        "BEGIN:VTODO",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{summary}",
        "STATUS:NEEDS-ACTION"
    ]
    if timed and start_date and end_date:
        # Optional timed due range (rare for VTODO)
        lines.append(f"DTSTART:{start_date.strftime('%Y%m%dT%H%M%S')}")
        lines.append(f"DUE:{end_date.strftime('%Y%m%dT%H%M%S')}")
    else:
        # All-day task
        lines.append(f"DUE;VALUE=DATE:{due_date.strftime('%Y%m%d')}")
    lines.append("END:VTODO")
    return "\n".join(lines) + "\n"

# --- FETCH TASKS FROM NOTION ---
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
res = requests.post(url, headers=headers)
data = res.json()

# --- CREATE VTODO CALENDARS PER CATEGORY ---
calendars = defaultdict(list)

for item in data.get("results", []):
    props = item.get("properties", {})

    # Task title
    title_prop = props.get("Tasks planned", {}).get("title", [])
    title = title_prop[0]["plain_text"] if title_prop else "Untitled"

    # Task date
    date_info = props.get("Date", {}).get("date")
    if not date_info or "start" not in date_info:
        continue

    # Parse start date and filter by cutoff
    event_start = datetime.fromisoformat(date_info["start"].replace("Z", "+00:00"))
    if event_start < CUTOFF_DATE:
        continue

    # Task category (Select)
    category_select = props.get("Category", {}).get("select")
    category_name = clean_text(category_select.get("name", "Other")) if category_select else "Other"

    # Determine all-day vs timed
    start_str = date_info["start"]
    end_str = date_info.get("end")

    if "T" not in start_str:  # all-day
        due_date = datetime.fromisoformat(start_str)
        vtodo_str = create_vtodo(uid=item["id"], summary=title, due_date=due_date)
    else:  # timed task
        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")) if end_str else start_dt
        vtodo_str = create_vtodo(uid=item["id"], summary=title, due_date=start_dt, timed=True, start_date=start_dt, end_date=end_dt)

    # Add to category calendar
    calendars[category_name].append(vtodo_str)

# --- SAVE ICS FILES PER CATEGORY ---
for category, todos in calendars.items():
    filename = f"docs/{category.lower()}_tasks.ics"
    with open(filename, "w") as f:
        f.write("BEGIN:VCALENDAR\nVERSION:2.0\n")
        for todo in todos:
            f.write(todo)
        f.write("END:VCALENDAR\n")
