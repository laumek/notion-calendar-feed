import requests
from ics import Calendar, Event
from collections import defaultdict
import os
import re
from datetime import datetime

# --- CONFIG ---
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")
CUTOFF_DATE = datetime(2025, 7, 1)  # Only events on/after this date

# --- HELPERS ---
def clean_text(s):
    """Remove emojis, links, and special characters from text."""
    return re.sub(r"[^\w\s-]", "", s)

# --- FETCH EVENTS FROM NOTION ---
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
res = requests.post(url, headers=headers)
data = res.json()

# --- CREATE CALENDARS PER CATEGORY ---
calendars = defaultdict(Calendar)

for item in data.get("results", []):
    props = item.get("properties", {})

    # Event title
    title_prop = props.get("Tasks planned", {}).get("title", [])
    title = title_prop[0]["plain_text"] if title_prop else "Untitled"

    # Event date
    date_info = props.get("Date", {}).get("date")
    if not date_info or "start" not in date_info:
        continue

    # Parse start date and filter by cutoff
    event_start = datetime.fromisoformat(date_info["start"].replace("Z", "+00:00"))
    if event_start < CUTOFF_DATE:
        continue

    # Event category (Select)
    category_select = props.get("Category", {}).get("select")
    category_name = clean_text(category_select.get("name", "Other")) if category_select else "Other"

    # Create ICS event
    e = Event()
    e.name = title
    e.begin = date_info["start"]
    if "end" in date_info and date_info["end"]:
        e.end = date_info["end"]

    # Add to category calendar
    calendars[category_name].events.add(e)

# Save separate ICS files per category
for category, cal in calendars.items():
    filename = f"docs/{category.lower()}.ics"
    with open(filename, "w") as f:
        f.writelines(cal)
