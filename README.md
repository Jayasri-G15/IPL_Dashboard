# IPL Analytics Dashboard

Custom deployable IPL analytics web app built with FastAPI, vanilla HTML/CSS/JavaScript, and the Cricsheet JSON dataset.

## What It Includes

- Custom non-Streamlit UI with responsive pages, IPL-style colors, image-backed sections, dark/light mode, and smooth navigation.
- FastAPI backend serving both the dashboard and the analytics API.
- Team performance, player rankings, toss impact, venue trends, data quality, and an IPL chatbot.
- Local logo support through `static/assets/team-logos/`.
- Fault-tolerant parser that skips or flags imperfect records instead of crashing.

## Run Locally

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Team Logos

Place official or approved team logo files in:

```text
static/assets/team-logos/
```

The frontend looks for names such as:

```text
chennai-super-kings.png
mumbai-indians.png
royal-challengers-bengaluru.png
kolkata-knight-riders.png
rajasthan-royals.png
delhi-capitals.png
sunrisers-hyderabad.png
punjab-kings.png
gujarat-titans.png
lucknow-super-giants.png
```

If a logo file is missing, the dashboard shows a polished fallback badge.

## Deploy

### Render

This repo includes `render.yaml`.

1. Push the project to GitHub.
2. Create a new Render Blueprint or Web Service.
3. Render will use:

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Other Python Hosts

The included `Procfile` works for hosts that support Procfile-based Python web apps.

## Files

- `app.py` - FastAPI app, API endpoints, and static dashboard serving.
- `pipeline.py` - Cricsheet parser and analytics pipeline.
- `static/index.html` - dashboard HTML shell.
- `static/styles.css` - custom UI styling.
- `static/app.js` - filters, navigation, charts, logo handling, and chatbot.
- `ipl_json.zip` - included Cricsheet IPL dataset.
- `REPORT.md` - project decisions, fault tolerance, testing notes.
