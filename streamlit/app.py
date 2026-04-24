"""Odissei Lifecourse Dataset Explorer - Streamlit App.

Interactive dashboard for exploring CBS dataset metadata from the ODISSEI Knowledge Graph.
"""

from datetime import date
from pathlib import Path
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import polars as pl
import streamlit as st

# --- Configuration ---
DB_PATH = Path(__file__).parent.parent / "data" / "event_datasets.duckdb"
CSV_PATH = Path(__file__).parent.parent / "data" / "Datasets 9424.csv"

# --- Page Config ---
st.set_page_config(
    page_title="Odissei Lifecourse Dataset Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Database Connection ---
def get_connection():
    """Get read-only DuckDB connection."""
    if not DB_PATH.exists():
        st.error(
            f"Database not found at `{DB_PATH}`.\n\nPlease run `python build_database.py` first to create the database."
        )
        st.stop()
    return duckdb.connect(str(DB_PATH), read_only=True)


# --- Data Loading (Cached) ---
@st.cache_data
def load_datasets():
    """Load dataset metadata from DuckDB."""
    con = get_connection()
    df = con.sql("""
        SELECT
            alt_title,
            title,
            description,
            dataset_id,
            is_tijdstip_dataset,
            is_frequency_dataset,
            valid_from,
            valid_until,
            keywords,
            publication_date,
            sampling_procedure
        FROM kg_datasets
    """).pl()
    con.close()
    return df


@st.cache_data
def load_variables():
    """Load variable metadata from DuckDB."""
    con = get_connection()
    df = con.sql("""
        SELECT
            dataset_id,
            variable_name,
            is_tijdstip,
            data_type,
            description
        FROM kg_variables
    """).pl()
    con.close()
    return df


@st.cache_data
def load_csv_datasets():
    """Load the reference CSV datasets."""
    if not CSV_PATH.exists():
        return None
    return pl.read_csv(CSV_PATH)


# --- Data Processing ---
def get_unique_keywords(df):
    """Extract unique keywords from list column."""
    all_keywords = []
    for kw_list in df["keywords"].to_list():
        if kw_list:
            all_keywords.extend(kw_list)
    return sorted(set(all_keywords))


def filter_datasets(df, selected_keywords, dataset_types, min_datasets):
    """Apply filters to dataset dataframe (no date filtering - truncation happens in visualization)."""
    filtered = df

    # Keyword filter - simpler approach using list contains
    if selected_keywords:
        # Build OR condition for each keyword
        keyword_conditions = None
        for kw in selected_keywords:
            # Check if any element in the keywords list equals this keyword
            condition = pl.col("keywords").list.contains(kw)
            if keyword_conditions is None:
                keyword_conditions = condition
            else:
                keyword_conditions = keyword_conditions | condition

        if keyword_conditions is not None:
            filtered = filtered.filter(keyword_conditions)

    # Dataset type filter
    if dataset_types:
        type_conditions = []
        if "tijdstip" in dataset_types:
            type_conditions.append(pl.col("is_tijdstip_dataset"))
        if "frequency" in dataset_types:
            type_conditions.append(pl.col("is_frequency_dataset"))
        if "both" in dataset_types:
            type_conditions.append(pl.col("is_tijdstip_dataset") & pl.col("is_frequency_dataset"))
        if type_conditions:
            filtered = filtered.filter(pl.any_horizontal(type_conditions))

    return filtered


def prepare_timeline_data(df, truncate_left, truncate_right):
    """Prepare data for Gantt chart with date truncation and break detection.

    Mimics the notebook SQL logic:
    - GREATEST(truncate_left, valid_from): truncate early dates to left boundary
    - COALESCE(valid_until, truncate_right): fill null end dates with right boundary
    - Groups by alt_title and collects breaks (valid_until dates that represent gaps)
    """
    # First truncate dates at the individual dataset level
    df = df.with_columns(
        [
            pl.when(pl.col("valid_from").is_null() | (pl.col("valid_from") < pl.lit(truncate_left)))
            .then(pl.lit(truncate_left))
            .otherwise(pl.col("valid_from"))
            .alias("valid_from"),
            pl.when(pl.col("valid_until").is_null())
            .then(pl.lit(truncate_right))
            .otherwise(pl.col("valid_until"))
            .alias("valid_until"),
        ]
    )

    # Aggregate by alt_title to find overall availability and breaks
    # Similar to notebook: GROUP BY alt_title, list(DISTINCT valid_until) as breaks
    aggregated = df.group_by("alt_title").agg(
        [
            pl.min("valid_from").alias("valid_from"),
            pl.max("valid_until").alias("valid_until"),
            # Collect valid_until dates as breaks (dataset ID changes/period ends)
            # Only include breaks that are before the right truncation (i.e., real breaks, not ongoing)
            pl.col("valid_until").filter(pl.col("valid_until") < pl.lit(truncate_right)).unique().alias("breaks"),
            # Keep boolean flags for summary stats (True if any row has it)
            pl.max("is_tijdstip_dataset").alias("is_tijdstip_dataset"),
            pl.max("is_frequency_dataset").alias("is_frequency_dataset"),
            # Determine dataset type
            pl.when(pl.max("is_tijdstip_dataset") & pl.max("is_frequency_dataset"))
            .then(pl.lit("both"))
            .when(pl.max("is_tijdstip_dataset"))
            .then(pl.lit("tijdstip"))
            .otherwise(pl.lit("frequency"))
            .alias("dataset_type"),
            # Collect unique keywords from all rows
            pl.col("keywords").explode().unique().alias("keywords"),
        ]
    )

    return aggregated


# --- Visualizations ---
def make_gantt_chart(df, show_break_markers=True):
    """Create interactive Plotly Gantt chart with break markers."""
    color_map = {
        "tijdstip": "#2ca02c",
        "frequency": "#ff7f0e",
        "both": "#1f77b4",
    }

    # Sort by valid_from in ascending order (earliest first)
    # With reversed y-axis, earliest dates will appear at top
    df = df.sort("valid_from", descending=False)

    # Cap height at 800px for scrollability when many datasets
    # Use fixed cell height of 25px, but max out at 800px
    n_datasets = len(df)
    fig_height = min(800, max(400, n_datasets * 25))

    # Use description (title) for y-axis labels, but keep alt_title for reference
    fig = px.timeline(
        df.to_pandas(),
        x_start="valid_from",
        x_end="valid_until",
        y="alt_title",
        color="dataset_type",
        color_discrete_map=color_map,
        height=fig_height,
        labels={"alt_title": "Dataset"},
    )

    # Add break markers as shape annotations (actual vertical lines)
    # These mark points where a dataset ID changed (period breaks)
    if show_break_markers and "breaks" in df.columns:
        breaks_df = df.select(["alt_title", "breaks"]).explode("breaks").filter(pl.col("breaks").is_not_null())

        if len(breaks_df) > 0:
            # Get y-axis categories to find positions
            y_categories = df["alt_title"].to_list()

            shapes = []
            for row in breaks_df.iter_rows(named=True):
                alt_title = row["alt_title"]
                break_date = row["breaks"]

                if alt_title in y_categories:
                    # Find the position in the y-axis (0-indexed)
                    y_pos = y_categories.index(alt_title)

                    # Add vertical line shape
                    shapes.append(
                        dict(
                            type="line",
                            x0=break_date,
                            x1=break_date,
                            y0=y_pos - 0.4,  # Slightly above the bar center
                            y1=y_pos + 0.4,  # Slightly below the bar center
                            line=dict(color="#444444", width=2),
                            xref="x",
                            yref="y",
                        )
                    )

            # Add invisible scatter for legend entry (no hover)
            if shapes:
                fig.add_trace(
                    go.Scatter(
                        x=[None],
                        y=[None],
                        mode="lines",
                        line=dict(color="#444444", width=2),
                        name="Dataset ID change",
                        hoverinfo="skip",
                    )
                )
                fig.update_layout(shapes=shapes)

    # Reverse y-axis so earliest dates (at end of sorted list) appear at top
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Dataset",
        legend_title="Dataset Type",
        hovermode=False,  # Disable all hover
        # Keep x-axis fixed at bottom when scrolling
        xaxis=dict(
            rangeslider=dict(visible=False),  # Disable range slider
            side="bottom",  # Keep at bottom
        ),
        # Enable scroll behavior
        dragmode="pan",  # Pan mode for easier navigation
    )

    # Disable hover on all traces
    fig.update_traces(hoverinfo="skip")

    return fig


# --- Main App ---
def main():
    st.title("📊 Odissei Lifecourse Dataset Explorer")
    st.markdown("Explore CBS dataset metadata from the ODISSEI Knowledge Graph.")

    # Load data
    with st.spinner("Loading data..."):
        datasets_df = load_datasets()
        variables_df = load_variables()
        csv_df = load_csv_datasets()

    # --- Sidebar Filters ---
    st.sidebar.header("🔍 Filters")

    # Get unique keywords
    unique_keywords = get_unique_keywords(datasets_df)

    selected_keywords = st.sidebar.multiselect(
        "Keywords",
        options=unique_keywords,
        default=[],
        help="Select one or more keywords to filter datasets",
    )

    dataset_types = st.sidebar.multiselect(
        "Dataset Type",
        options=["tijdstip", "frequency", "both"],
        default=["tijdstip", "frequency", "both"],
        format_func=lambda x: {
            "tijdstip": "Tijdstip Dataset",
            "frequency": "Frequency Dataset",
            "both": "Both Types",
        }[x],
    )

    min_datasets = st.sidebar.slider(
        "Minimum datasets per keyword",
        min_value=0,
        max_value=50,
        value=10,
        help="Only show keywords with at least this many datasets",
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date(1995, 1, 1),
            min_value=date(1990, 1, 1),
            max_value=date(2026, 12, 31),
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date(2026, 12, 31),
            min_value=date(1990, 1, 1),
            max_value=date(2026, 12, 31),
        )

    # Apply filters (no date filtering - truncation happens in visualization)
    filtered_df = filter_datasets(datasets_df, selected_keywords, dataset_types, min_datasets)

    st.sidebar.markdown(f"**{len(filtered_df)} datasets selected**")

    # Prepare timeline data if we have datasets (used by both sidebar explorer and timeline tab)
    timeline_df = None
    if len(filtered_df) > 0 and len(filtered_df) <= 1000:
        timeline_df = prepare_timeline_data(filtered_df, start_date, end_date)

    # --- Sidebar: Chart Options (placed before dataset explorer) ---
    if timeline_df is not None and len(timeline_df) > 0:
        st.sidebar.divider()
        st.sidebar.subheader("📊 Chart Options")

        # Initialize session state for break markers if not exists
        if "show_break_markers" not in st.session_state:
            st.session_state.show_break_markers = False

        def on_break_marker_toggle():
            """Callback when break marker toggle changes."""
            st.session_state.show_break_markers = st.session_state.break_marker_checkbox

        st.sidebar.checkbox(
            "Show dataset ID change markers",
            value=st.session_state.show_break_markers,
            key="break_marker_checkbox",
            on_change=on_break_marker_toggle,
            help="Show vertical gray lines indicating where a dataset's ID changed over time. Best viewed when zoomed in on a few datasets. Note: toggling this will reset the chart zoom.",
        )

    # --- Sidebar: Dataset Details Explorer (isolated in fragment to prevent chart refresh) ---
    @st.fragment
    def render_dataset_explorer_fragment(timeline_df, filtered_df):
        """Render the dataset explorer as a fragment (called inside sidebar context)."""
        if timeline_df is not None and len(timeline_df) > 0:
            st.divider()
            st.subheader("📋 Explore Dataset Details")

            # Get the list of datasets shown in the timeline
            timeline_datasets = timeline_df["alt_title"].to_list()

            # Initialize session state for the selected dataset if not exists
            if "selected_dataset" not in st.session_state:
                st.session_state.selected_dataset = timeline_datasets[0] if timeline_datasets else None

            # Determine the current index based on session state
            current_selection = st.session_state.selected_dataset
            if current_selection in timeline_datasets:
                current_index = timeline_datasets.index(current_selection)
            else:
                current_index = 0
                st.session_state.selected_dataset = timeline_datasets[0] if timeline_datasets else None

            def on_dataset_change():
                """Callback to update session state when selection changes."""
                st.session_state.selected_dataset = st.session_state.dataset_selector

            selected_detail_dataset = st.selectbox(
                "Select a dataset",
                options=timeline_datasets,
                index=current_index,
                key="dataset_selector",
                on_change=on_dataset_change,
                help="Choose a dataset from the timeline to see its details",
            )

            if selected_detail_dataset:
                # Get full details from the original filtered dataframe
                dataset_details = filtered_df.filter(pl.col("alt_title") == selected_detail_dataset)

                if len(dataset_details) > 0:
                    # Get the first row as a dict for easy access
                    row = dataset_details.to_dicts()[0]

                    # Determine dataset type label
                    if row["is_tijdstip_dataset"] and row["is_frequency_dataset"]:
                        type_label = "Both"
                        type_color = "blue"
                    elif row["is_tijdstip_dataset"]:
                        type_label = "Event"
                        type_color = "green"
                    else:
                        type_label = "Frequency"
                        type_color = "orange"

                    # Compact display in sidebar
                    st.markdown(f"**{row['title'][:80]}{'...' if len(row['title']) > 80 else ''}**")
                    st.caption(f"Code: `{selected_detail_dataset}`")
                    st.markdown(
                        f"<span style='color:{type_color}; font-weight:bold;'>● {type_label}</span> · "
                        f"📅 {row['valid_from']} → {row.get('valid_until') or 'Present'}",
                        unsafe_allow_html=True,
                    )

                    # Keywords
                    keywords_val = row.get("keywords")
                    if keywords_val is not None and len(keywords_val) > 0:
                        keywords_str = ", ".join(keywords_val[:5])  # Limit to 5 in sidebar
                        if len(keywords_val) > 5:
                            keywords_str += f" (+{len(keywords_val) - 5} more)"
                        st.markdown(f"🏷️ {keywords_str}")

                    # Dataset ID as link
                    st.markdown(f"🔗 [{row['dataset_id'][:50]}...]({row['dataset_id']})")

                    # Description in expandable section
                    description = row.get("description")
                    has_description = bool(
                        description is not None and str(description).strip() and str(description).lower() != "none"
                    )

                    with st.expander("📊 Description", expanded=has_description):
                        if has_description:
                            st.write(description)
                        else:
                            st.caption("No description available.")

    # Render the fragment inside sidebar context - this runs independently without triggering chart refresh
    with st.sidebar:
        render_dataset_explorer_fragment(timeline_df, filtered_df)

    # --- Main Content Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📈 Timeline",
            "📋 Dataset Table",
            "🔄 Comparison",
            "🔍 Variables",
        ]
    )

    # Tab 1: Timeline
    with tab1:
        st.header("Dataset Availability Timeline")

        # Help text for navigation
        if len(filtered_df) > 30:
            st.info(
                "💡 **Tip:** Use your mouse wheel to zoom and drag to pan. The plot shows all datasets at once - scroll or use the mode bar (top-right) to navigate."
            )

        if len(filtered_df) == 0:
            st.warning("No datasets match the selected filters.")
        elif len(filtered_df) > 1000:
            st.warning(f"Too many datasets ({len(filtered_df)}) to display. Please apply more filters.")
        elif timeline_df is not None:
            n_datasets = len(timeline_df)

            # Warn when many datasets may have hidden labels
            if n_datasets > 32:
                st.info(
                    f"📊 **{n_datasets} datasets** in result set. Without zooming, not all datasets may be displayed at once. "
                    f"Use the **zoom and pan controls** in the chart's top-right toolbar to explore all datasets.",
                    icon="ℹ️",
                )

            # Get break marker preference from session state (default False for cleaner view)
            show_markers = st.session_state.get("show_break_markers", False)
            fig = make_gantt_chart(timeline_df, show_break_markers=show_markers)

            # Wrap in a scrollable container with fixed x-axis feel
            # Use native plotly scroll/zoom for large datasets
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "scrollZoom": True,  # Enable scroll to zoom
                    "displayModeBar": True,  # Show zoom/pan controls
                },
            )

            # Summary statistics (using aggregated boolean columns)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Event Datasets", int(timeline_df["is_tijdstip_dataset"].sum()))
            with col2:
                st.metric(
                    "Frequency Datasets",
                    int(timeline_df["is_frequency_dataset"].sum()),
                )
            with col3:
                st.metric(
                    "Both Types",
                    int((timeline_df["is_tijdstip_dataset"] & timeline_df["is_frequency_dataset"]).sum()),
                )

    # Tab 2: Dataset Table
    with tab2:
        st.header("Dataset Details")

        if len(filtered_df) == 0:
            st.warning("No datasets match the selected filters.")
        else:
            # Prepare display dataframe
            display_df = filtered_df.with_columns(
                [
                    pl.col("keywords").list.join(", ").alias("keywords_str"),
                    pl.when(pl.col("is_tijdstip_dataset") & pl.col("is_frequency_dataset"))
                    .then(pl.lit("both"))
                    .when(pl.col("is_tijdstip_dataset"))
                    .then(pl.lit("tijdstip"))
                    .otherwise(pl.lit("frequency"))
                    .alias("type"),
                ]
            ).select(
                [
                    "alt_title",
                    "title",
                    "type",
                    "keywords_str",
                    "valid_from",
                    "valid_until",
                ]
            )

            st.dataframe(
                display_df.to_pandas(),
                use_container_width=True,
                hide_index=True,
            )

    # Tab 3: Comparison
    with tab3:
        st.header("KG vs Datasets 9424.csv Comparison")

        if csv_df is None:
            st.warning(f"Reference CSV not found at `{CSV_PATH}`.")
        else:
            kg_titles = set(filtered_df["alt_title"].to_list())
            csv_titles = set(csv_df["Bestandsnaam"].to_list())

            in_both = kg_titles & csv_titles
            in_kg_only = kg_titles - csv_titles
            in_csv_only = csv_titles - kg_titles

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("In Both", len(in_both))
            with col2:
                st.metric("In KG Only", len(in_kg_only))
            with col3:
                st.metric("In CSV Only", len(in_csv_only))

            # Show details
            with st.expander("Datasets in both"):
                if in_both:
                    st.write(sorted(in_both))
                else:
                    st.write("None")

            with st.expander("Datasets in KG only"):
                if in_kg_only:
                    st.write(sorted(in_kg_only))
                else:
                    st.write("None")

            with st.expander("Datasets in CSV only"):
                if in_csv_only:
                    st.write(sorted(in_csv_only))
                else:
                    st.write("None")

    # Tab 4: Variables
    with tab4:
        st.header("Variable Explorer")

        # Dataset selector
        dataset_options = filtered_df["alt_title"].to_list()
        if not dataset_options:
            st.warning("No datasets match the selected filters.")
        else:
            selected_dataset = st.selectbox(
                "Select a dataset",
                options=dataset_options,
                help="Choose a dataset to view its variables",
            )

            if selected_dataset:
                # Get dataset_id
                dataset_id = filtered_df.filter(pl.col("alt_title") == selected_dataset)["dataset_id"][0]

                # Get variables
                vars_df = variables_df.filter(pl.col("dataset_id") == dataset_id)

                if len(vars_df) == 0:
                    st.info("No variables found for this dataset.")
                else:
                    # Add type column
                    vars_display = vars_df.with_columns(
                        [
                            pl.when(pl.col("is_tijdstip"))
                            .then(pl.lit("timestamp"))
                            .otherwise(pl.lit("other"))
                            .alias("type"),
                        ]
                    ).select(
                        [
                            "variable_name",
                            "type",
                            "data_type",
                        ]
                    )

                    st.write(f"**{len(vars_df)} variables**")

                    # Show timestamp variables first
                    timestamp_vars = vars_display.filter(pl.col("type") == "timestamp")
                    other_vars = vars_display.filter(pl.col("type") != "timestamp")

                    if len(timestamp_vars) > 0:
                        st.subheader("⏰ Timestamp Variables")
                        st.dataframe(
                            timestamp_vars.to_pandas(),
                            use_container_width=True,
                            hide_index=True,
                        )

                    if len(other_vars) > 0:
                        st.subheader("📋 Other Variables")
                        st.dataframe(
                            other_vars.to_pandas(),
                            use_container_width=True,
                            hide_index=True,
                        )


if __name__ == "__main__":
    main()
