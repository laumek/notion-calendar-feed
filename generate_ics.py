import requests
from ics import Calendar, Event
from collections import defaultdict
import os
import re

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
res = requests.post(url, headers=headers)
data = res.json()

# Helper to clean text (remove emojis/links)
def clean_text(s):
    return re.sub(r"[^\w\s-]", "", s)

# Dictionary to hold separate calendars per category
calendars = defaultdict(Calendar)

for item in data["results"]:
    props = item["properties"]

    # Event title
    title_prop = props.get("Tasks planned", {}).get("title", [])
    title = title_prop[0]["plain_text"] if title_prop else "Untitled"

    # Event date
    date_info = props.get("Date", {}).get("date")
    if not date_info or "start" not in date_info:
        continue

    # Single category from Relation
    category_relation = props.get("Category", {}).get("relation", [])
    if category_relation:
        # Take the first related page and clean text
        category_name_raw = category_relation[0].get("title", "")
        category_name = clean_text(category_name_raw) or "Other"
    else:
        category_name = "Other"

    # Create event
    e = Event()
    e.name = title
    e.begin = date_info["start"]
    if "end" in date_info and date_info["end"]:
        e.end = date_info["end"]

    # Add to calendar for this category
    calendars[category_name].events.add(e)

# Save separate ICS files per category
for category, cal in calendars.items():
    filename = f"docs/{category.lower()}.ics"
    with open(filename, "w") as f:
        f.writelines(cal)
