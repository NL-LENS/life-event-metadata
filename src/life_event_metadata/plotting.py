import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import polars as pl


# ruff: disable[PLR0913]
def make_gantt_chart(
    plot_df: pl.DataFrame,
    category_column: str,
    yaxis_column: str,
    category_mapping: dict,
    title: str = "Dataset Availability Timeline",
    xlabel: str = "Date",
) -> None:
    """Make a gantt chart of a dataset or a variable.

    Parameters
    ----------
    plot_df: pl.DataFrame
        Rows to plot.
    category_column: str
        Column name of the category for setting colors.
    yaxis_column: str
        Column for y-axis labels. Ie, dataset names or column names.
    category_mapping: dict
        Mapping of categories to colors.
    title: str
        Title of the chart.
    xlabel: str
        Label of the x-axis.
    """
    # TODO: plot height scales with the size of the df,
    # but there a white gap top and bottom that also scales with it
    plot_df = plot_df.with_row_index("row_idx")
    _, ax = plt.subplots(figsize=(14, max(6, len(plot_df) * 0.3)))

    for label, color in category_mapping.items():
        subset = plot_df.filter(pl.col(category_column) == label)

        if not subset.is_empty():
            starts = mdates.date2num(subset["first_available"].to_list())
            ends = mdates.date2num(subset["last_available"].to_list())
            durations = ends - starts
            y_pos = subset["row_idx"].to_list()

            ax.barh(y_pos, durations, left=starts, height=0.7, color=color, label=label, alpha=0.7)

    breaks_df = pl.DataFrame()
    if "breaks" in plot_df.columns:
        breaks_df = plot_df.select(["row_idx", "breaks"]).explode("breaks").filter(pl.col("breaks").is_not_null())

    if not breaks_df.is_empty():
        break_x = mdates.date2num(breaks_df["breaks"].to_list())
        break_y = breaks_df["row_idx"].to_list()

        ax.scatter(break_x, break_y, marker="|", color="red", s=200, linewidth=2, zorder=3, label="Dataset ID change")

    ax.set_yticks(range(len(plot_df)))
    ax.set_yticklabels(plot_df[yaxis_column].to_list(), fontsize=9)
    ax.set_xlabel(xlabel)
    ax.set_title(title)

    ax.legend(loc="upper left", bbox_to_anchor=(1, 1))

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# ruff: enable[PLR0913]
