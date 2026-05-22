# IPL Analytics Dashboard

Interactive Streamlit dashboard for Cricsheet IPL JSON data.

## What it does

- Cleans and parses Cricsheet match JSON from a ZIP archive or folder of JSON files.
- Handles malformed files and partial records without failing the full pipeline.
- Builds team, batting, bowling, toss, and venue summaries.
- Visualizes the results with interactive Plotly charts in Streamlit.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

By default the app looks for `ipl_json.zip` in the project root. You can also upload a ZIP from the sidebar or point the app at another Cricsheet-compatible ZIP/JSON folder.

## Data source

This project is built against the Cricsheet JSON schema.