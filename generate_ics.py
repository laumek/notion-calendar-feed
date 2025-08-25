import requests
from ics import Calendar, Event
from datetime import datetime
import os

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"


# Fetch events from Notion

res = requests.post(url, headers=headers)
data = res.json()

cal = Calendar()

for item in data["results"]:
    props = item["properties"]
    title = props["Tasks planned"]["title"][0]["plain_text"] if props["Tasks planned"]["title"] else "Untitled"
    date_info = props["Date"]["date"]

    if date_info and "start" in date_info:
        e = Event()
        e.name = title
        e.begin = date_info["start"]
        if "end" in date_info and date_info["end"]:
            e.end = date_info["end"]
        cal.events.add(e)

# Save ICS file
with open("docs/notion_calendar.ics", "w") as f:
    f.writelines(cal)
