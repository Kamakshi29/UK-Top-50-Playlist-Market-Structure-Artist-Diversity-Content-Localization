"""
UK Top 50 Playlist — Market Structure, Artist Diversity & Content Localization Dashboard
Atlantic Recording Corporation | Unified Mentor Project

Run with:  streamlit run app.py
Expects the cleaned dataset at ./data/Atlantic_UK_Top50_CLEANED.csv
"""

import ast
import itertools
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="UK Top 50 Market Structure Dashboard",
    page_icon="\U0001F3B5",
    layout="wide",
)

DATA_NAME = "Atlantic_UK_Top50_CLEANED.csv"

try:
    _NEW_ST = tuple(int(x) for x in st.__version__.split(".")[:2]) >= (1, 50)
except Exception:
    _NEW_ST = False


def show_chart(fig):
    """Works on both older and newer Streamlit versions."""
    st.plotly_chart(fig, **({"width": "stretch"} if _NEW_ST else {"use_container_width": True}))


def show_table(d):
    st.dataframe(d, hide_index=True, **({"width": "stretch"} if _NEW_ST else {"use_container_width": True}))


def find_data():
    """Look next to app.py first (not just the working directory, which differs on Streamlit Cloud)."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "data" / DATA_NAME, here / DATA_NAME, here.parent / "data" / DATA_NAME,
        Path.cwd() / "data" / DATA_NAME, Path.cwd() / DATA_NAME,
    ]
    for p in candidates:
        if p.exists():
            return p, candidates
    for base in (here, Path.cwd()):
        hit = next(base.rglob(DATA_NAME), None)
        if hit:
            return hit, candidates
    return None, candidates


# ----------------------------------------------------------------------------
# Data loading & cleaning (mirrors the audited cleaning pipeline)
# ----------------------------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["chart_date"] = pd.to_datetime(df["chart_date"])
    df["artist_list"] = df["artist_list"].apply(ast.literal_eval)

    # Exclude the confirmed erroneous duplicate chart-day block (01-03-2025)
    df = df[df["date_anomaly_flag"] != "duplicate_date_block_RECOMMEND_EXCLUDE"].copy()

    df["rank_group"] = np.where(df["position"] <= 10, "Top 10", "Top 11-50")
    df["duration_min"] = df["duration_ms"] / 60000
    df["duration_bucket"] = pd.cut(
        df["duration_min"],
        bins=[0, 2.5, 3.0, 3.5, 4.0, 4.5, 100],
        labels=["<2:30", "2:30-3:00", "3:00-3:30", "3:30-4:00", "4:00-4:30", "4:30+"],
    )
    return df


_data_file, _tried = find_data()
if _data_file is None:
    st.error(
        f"Could not find **{DATA_NAME}**. Put it in a folder called `data` next to `app.py` in your repo. "
        "Places I looked:\n\n" + "\n".join(f"- `{p}`" for p in _tried)
    )
    st.stop()
try:
    df_all = load_data(str(_data_file))
except Exception as e:
    st.error(f"Found the data file at `{_data_file}` but could not read it: {type(e).__name__}: {e}")
    st.stop()

# ----------------------------------------------------------------------------
# Sidebar — User Capabilities (filters)
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")

min_date, max_date = df_all["chart_date"].min().date(), df_all["chart_date"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

all_artists = sorted(set(itertools.chain.from_iterable(df_all["artist_list"])))
artist_filter = st.sidebar.multiselect(
    "Artist filter (leave empty for all artists)",
    options=all_artists,
)

collab_toggle = st.sidebar.radio(
    "Solo vs. Collaboration",
    options=["All", "Solo only", "Collaborative only"],
    index=0,
)

album_types = sorted(df_all["album_type"].dropna().unique().tolist())
album_type_filter = st.sidebar.multiselect(
    "Album type filter (leave empty for all)",
    options=album_types,
)

# ----------------------------------------------------------------------------
# Apply filters
# ----------------------------------------------------------------------------
df = df_all[
    (df_all["chart_date"].dt.date >= start_date) & (df_all["chart_date"].dt.date <= end_date)
].copy()

if artist_filter:
    artist_set = set(artist_filter)
    df = df[df["artist_list"].apply(lambda lst: bool(artist_set.intersection(lst)))]

if collab_toggle == "Solo only":
    df = df[~df["is_collab"]]
elif collab_toggle == "Collaborative only":
    df = df[df["is_collab"]]

if album_type_filter:
    df = df[df["album_type"].isin(album_type_filter)]

if df.empty:
    st.warning("No chart entries match the current filters. Adjust filters in the sidebar.")
    st.stop()

exploded = df.explode("artist_list").rename(columns={"artist_list": "artist_atom"})

# ----------------------------------------------------------------------------
# Header & KPI row
# ----------------------------------------------------------------------------
st.title("\U0001F3B5 UK Top 50 — Market Structure & Artist Diversity Dashboard")
st.caption(
    f"Showing {len(df):,} chart entries across {df['chart_date'].nunique():,} days "
    f"({start_date} to {end_date})"
)

total_appearances = len(exploded)
unique_artists = exploded["artist_atom"].nunique()
artist_counts = exploded["artist_atom"].value_counts()
shares = artist_counts / total_appearances if total_appearances else pd.Series(dtype=float)
hhi = (shares ** 2).sum() if total_appearances else np.nan
top5_share = shares.head(5).sum() if total_appearances else np.nan
collab_ratio = df["is_collab"].mean() if len(df) else np.nan
explicit_share = df["is_explicit"].mean() if len(df) else np.nan
single_share = (df["album_type"] == "single").mean() if len(df) else np.nan
album_share = (df["album_type"] == "album").mean() if len(df) else np.nan
single_album_ratio = (single_share / album_share) if album_share else np.nan

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Artist Concentration (HHI)", f"{hhi:.4f}" if pd.notna(hhi) else "—")
k2.metric("Unique Artists", f"{unique_artists:,}")
k3.metric("Top-5 Concentration", f"{top5_share*100:.1f}%" if pd.notna(top5_share) else "—")
k4.metric("Collaboration Ratio", f"{collab_ratio*100:.1f}%" if pd.notna(collab_ratio) else "—")
k5.metric("Explicit Content Share", f"{explicit_share*100:.1f}%" if pd.notna(explicit_share) else "—")
k6.metric("Single : Album Ratio", f"{single_album_ratio:.2f}" if pd.notna(single_album_ratio) else "—")

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Artist Dominance",
        "Collaboration Network",
        "Explicit Content",
        "Album Structure",
        "Duration Insights",
    ]
)

# ----------------------------------------------------------------------------
# Module 1 — Artist Dominance Leaderboard
# ----------------------------------------------------------------------------
with tab1:
    st.subheader("Artist Dominance Leaderboard")
    top_n = st.slider("Number of artists to show", 5, 50, 15, key="dom_slider")
    leaderboard = artist_counts.head(top_n).reset_index()
    leaderboard.columns = ["Artist", "Appearances"]
    fig = px.bar(
        leaderboard.sort_values("Appearances"),
        x="Appearances",
        y="Artist",
        orientation="h",
        title=f"Top {top_n} Artists by Chart Appearances",
    )
    fig.update_layout(height=max(400, top_n * 24))
    show_chart(fig)

    per_day_unique = exploded.groupby("chart_date")["artist_atom"].nunique()
    st.caption(
        f"Average unique artists per day in current selection: **{per_day_unique.mean():.1f}** "
        f"(min {per_day_unique.min()}, max {per_day_unique.max()})"
    )

# ----------------------------------------------------------------------------
# Module 2 — Collaboration Network Visualization
# ----------------------------------------------------------------------------
with tab2:
    st.subheader("Collaboration Network")

    pair_rows = df[df["n_artists"] >= 2]
    pair_counter = Counter()
    for lst in pair_rows["artist_list"]:
        for a, b in itertools.combinations(sorted(set(lst)), 2):
            pair_counter[(a, b)] += 1

    if not pair_counter:
        st.info("No collaborations in the current filter selection.")
    else:
        top_pairs_n = st.slider("Number of top collaboration pairs to display", 5, 40, 20, key="pair_slider")
        pairs_df = (
            pd.DataFrame(
                [(a, b, c) for (a, b), c in pair_counter.items()],
                columns=["Artist A", "Artist B", "Days Co-charted"],
            )
            .sort_values("Days Co-charted", ascending=False)
            .head(top_pairs_n)
        )

        # Build a simple circular network layout (no extra graph-layout dependency)
        nodes = sorted(set(pairs_df["Artist A"]).union(pairs_df["Artist B"]))
        angle_step = 2 * np.pi / max(len(nodes), 1)
        pos = {n: (np.cos(i * angle_step), np.sin(i * angle_step)) for i, n in enumerate(nodes)}

        edge_x, edge_y = [], []
        for _, row in pairs_df.iterrows():
            x0, y0 = pos[row["Artist A"]]
            x1, y1 = pos[row["Artist B"]]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=1, color="rgba(150,150,150,0.5)"), hoverinfo="none",
        )
        node_x = [pos[n][0] for n in nodes]
        node_y = [pos[n][1] for n in nodes]
        node_size = [8 + 4 * sum(c for (a, b), c in pair_counter.items() if n in (a, b)) ** 0.5 for n in nodes]
        node_trace = go.Scatter(
            x=node_x, y=node_y, mode="markers+text", text=nodes, textposition="top center",
            marker=dict(size=node_size, line=dict(width=1)), hoverinfo="text",
        )
        net_fig = go.Figure(data=[edge_trace, node_trace])
        net_fig.update_layout(
            title="Collaboration Network (top pairs in current selection)",
            showlegend=False, height=650,
            xaxis=dict(visible=False), yaxis=dict(visible=False),
        )
        show_chart(net_fig)

        show_table(pairs_df)

        avg_collab = df.loc[df["is_collab"], "n_artists"].mean()
        st.caption(f"Average collaborators per collaborative track: **{avg_collab:.2f}**")

# ----------------------------------------------------------------------------
# Module 3 — Explicit vs Clean Content Analysis
# ----------------------------------------------------------------------------
with tab3:
    st.subheader("Explicit vs. Clean Content")
    col_a, col_b = st.columns(2)

    with col_a:
        pie_df = df["is_explicit"].map({True: "Explicit", False: "Clean"}).value_counts().reset_index()
        pie_df.columns = ["Content Type", "Entries"]
        fig_pie = px.pie(pie_df, names="Content Type", values="Entries", title="Overall Explicit vs. Clean Share")
        show_chart(fig_pie)

    with col_b:
        rank_explicit = (df.groupby("rank_group")["is_explicit"].mean() * 100).reset_index()
        rank_explicit.columns = ["Rank Group", "Explicit %"]
        fig_rank = px.bar(rank_explicit, x="Rank Group", y="Explicit %", title="Explicit Share by Rank Group")
        show_chart(fig_rank)

    pos_bucket = pd.cut(df["position"], bins=[0, 10, 20, 30, 40, 50],
                         labels=["1-10", "11-20", "21-30", "31-40", "41-50"])
    pos_explicit = (df.groupby(pos_bucket, observed=True)["is_explicit"].mean() * 100).reset_index()
    pos_explicit.columns = ["Position Bucket", "Explicit %"]
    fig_pos = px.line(pos_explicit, x="Position Bucket", y="Explicit %", markers=True,
                       title="Explicit Content Share by Chart Position")
    show_chart(fig_pos)

# ----------------------------------------------------------------------------
# Module 4 — Album Type Distribution
# ----------------------------------------------------------------------------
with tab4:
    st.subheader("Album Structure & Release Strategy")
    col_a, col_b = st.columns(2)

    with col_a:
        type_counts = df["album_type"].value_counts().reset_index()
        type_counts.columns = ["Album Type", "Entries"]
        fig_type = px.bar(type_counts, x="Album Type", y="Entries", title="Release Format Distribution")
        show_chart(fig_type)

    with col_b:
        fig_tracks = px.box(df, x="album_type", y="total_tracks", title="Album Size (total_tracks) by Release Type")
        show_chart(fig_tracks)

    multitrack_singles = int(df["single_multitrack_flag"].sum())
    st.caption(
        f"Flagged: **{multitrack_singles:,}** entries labeled 'single' with more than 1 track "
        f"(deluxe/edit versions) in the current selection."
    )

# ----------------------------------------------------------------------------
# Module 5 — Track Duration Insights
# ----------------------------------------------------------------------------
with tab5:
    st.subheader("Track Duration & Format Analysis")
    col_a, col_b = st.columns(2)

    with col_a:
        dur_counts = df["duration_bucket"].value_counts().sort_index().reset_index()
        dur_counts.columns = ["Duration Bucket", "Entries"]
        fig_dur = px.bar(dur_counts, x="Duration Bucket", y="Entries", title="Track Duration Distribution")
        show_chart(fig_dur)

    with col_b:
        dur_pop = df.groupby("duration_bucket", observed=True)["popularity_clean"].mean().reset_index()
        dur_pop.columns = ["Duration Bucket", "Avg Popularity"]
        fig_dp = px.bar(dur_pop, x="Duration Bucket", y="Avg Popularity", title="Avg Popularity by Duration Bucket")
        fig_dp.update_yaxes(range=[dur_pop["Avg Popularity"].min() - 5, dur_pop["Avg Popularity"].max() + 5])
        show_chart(fig_dp)

    skit_n = int(df["is_likely_skit"].sum())
    st.caption(
        f"Flagged: **{skit_n:,}** likely skit/interlude entries (sub-90-second tracks or "
        f"titled skit/interlude/intro) in the current selection — consider excluding these "
        f"before drawing duration-vs-popularity conclusions."
    )

st.divider()
st.caption(
    "Data: Atlantic UK Top 50 daily snapshots, cleaned & audited (see accompanying research paper "
    "for the full data-validation methodology). Built for the Unified Mentor project submission."
)
