import altair as alt
import pandas as pd


def render_food_chart(frame: pd.DataFrame, series: list[str], title: str) -> alt.Chart:
    chart_frame = frame.reset_index()[["entry_date", *series]].copy()
    chart_frame["entry_date"] = pd.to_datetime(chart_frame["entry_date"])
    chart_frame = chart_frame.sort_values("entry_date", ascending=True)

    for column in series:
        chart_frame[column] = pd.to_numeric(chart_frame[column], errors="coerce")

    melted = chart_frame.melt("entry_date", var_name="series", value_name="value")
    value_min = melted["value"].min(skipna=True)
    value_max = melted["value"].max(skipna=True)

    if pd.isna(value_min) or pd.isna(value_max):
        value_min, value_max = 0.0, 1.0
    elif value_min == value_max:
        padding = max(abs(value_min) * 0.1, 1.0)
        value_min -= padding
        value_max += padding
    else:
        padding = (value_max - value_min) * 0.08
        value_min -= padding
        value_max += padding

    base = alt.Chart(melted).encode(
        x=alt.X("entry_date:T", title="Date", sort="ascending"),
        y=alt.Y(
            "value:Q",
            title=None,
            scale=alt.Scale(domain=[float(value_min), float(value_max)], reverse=False, nice=False, zero=False),
        ),
        color=alt.Color("series:N", title=None),
        detail="series:N",
        tooltip=[
            alt.Tooltip("yearmonthdate(entry_date):T", title="Date"),
            alt.Tooltip("series:N", title="Series"),
            alt.Tooltip("value:Q", title="Value", format=".2f"),
        ],
    )

    return base.transform_filter("isValid(datum.value)").mark_line(point=True).properties(height=260, title=title)
