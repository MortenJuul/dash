import altair as alt
import pandas as pd


SERIES_LABELS = {
    "calories": "Calories",
    "calories_target": "Calorie target",
    "protein_g": "Protein",
    "fat_g": "Fat",
    "carbs_g": "Carbs",
    "fiber_g": "Fiber",
    "water_liters": "Water",
    "water_target_liters": "Water target",
}


def render_food_chart(frame: pd.DataFrame, series: list[str], title: str) -> alt.Chart:
    chart_frame = frame.reset_index()[["entry_date", *series]].copy()
    chart_frame["entry_date"] = pd.to_datetime(chart_frame["entry_date"])
    chart_frame = chart_frame.sort_values("entry_date", ascending=True)

    for column in series:
        chart_frame[column] = pd.to_numeric(chart_frame[column], errors="coerce")

    melted = chart_frame.melt("entry_date", var_name="series", value_name="value")
    melted = melted.dropna(subset=["value"]).copy()
    melted["label"] = melted["series"].map(SERIES_LABELS).fillna(melted["series"])
    melted["date_label"] = melted["entry_date"].dt.strftime("%Y-%m-%d")

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
        color=alt.Color("label:N", title=None),
        detail="label:N",
    )

    line = base.mark_line(strokeWidth=2.5)
    points = base.mark_circle(size=80, opacity=0.9).encode(
        tooltip=[
            alt.Tooltip("date_label:N", title="Date"),
            alt.Tooltip("label:N", title="Series"),
            alt.Tooltip("value:Q", title="Value", format=".2f"),
        ]
    )

    return (line + points).properties(height=260, title=title).interactive()
