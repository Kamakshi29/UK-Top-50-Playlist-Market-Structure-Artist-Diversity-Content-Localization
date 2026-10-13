# UK Top 50 Market Structure Dashboard

Streamlit dashboard for the Atlantic Recording Corporation / Unified Mentor
"UK Top 50 Playlist Market Structure, Artist Diversity & Content Localization" project.

## Setup

```bash
cd streamlit_dashboard
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Opens at http://localhost:8501 by default.

## Data

The app reads `data/Atlantic_UK_Top50_CLEANED.csv` — the audited, cleaned dataset
(27,800 rows, with derived columns for artist splitting, collaboration flags,
popularity-missing flags, duplicate-day flags, skit flags, etc.). See the
accompanying research paper for the full cleaning methodology. The app
automatically excludes the 50 rows flagged as the duplicate `01-03-2025`
chart-day anomaly.

To refresh with newer data, replace that file with an updated export that has
the same column structure (or re-run the cleaning pipeline described in the
research paper on a new raw export first — don't point this app at the raw,
uncleaned CSV directly).

## What's in the dashboard

- **KPI row**: Artist Concentration Index (HHI), Unique Artist Count, Top-5
  Concentration, Collaboration Ratio, Explicit Content Share, Single:Album Ratio
  — recalculated live from whatever filters are active.
- **Artist Dominance** tab: leaderboard of top artists by chart appearances.
- **Collaboration Network** tab: node/edge visualization of the most frequent
  collaborator pairs in the current selection, plus a sortable table.
- **Explicit Content** tab: overall split, by rank group, and by position bucket.
- **Album Structure** tab: single/album/compilation distribution and album-size
  comparison.
- **Duration Insights** tab: duration distribution and average popularity by
  duration bucket.

## Filters (sidebar)

- Date range selector
- Artist filter (multi-select, matches any row containing the selected artist(s))
- Solo vs. Collaboration toggle
- Album type filter

## Known limitations carried over from the research paper

- No artist-nationality field exists in the source data, so a domestic-vs-
  international filter/KPI is **not** included here — see the research paper's
  Section 4.7 for why, and what's needed to add it.
- The Content Variety Index described in the research paper is a constructed
  composite metric, not shown in this dashboard build; add it as a KPI tile if
  stakeholders sign off on the formula.
