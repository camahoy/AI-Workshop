"""True-scatter Agency Map: participants click an exact x/y position on a
2D grid (x = AI involvement, y = drudgery→judgment) rather than picking one
of four buckets. Click capture works by overlaying a dense, near-invisible
grid of Plotly markers and reading back which grid point Streamlit's
on_select event resolved the click to (~4% resolution — far finer than
four quadrants, without needing a custom component).

Note: the grid trace uses hoverinfo="none", NOT "skip" — Plotly's "skip"
also unbinds the click/select handler for that trace, which silently
breaks click capture.
"""
import plotly.graph_objects as go

GRID_STEP = 4
_GRID_VALS = list(range(0, 101, GRID_STEP))
_GX = [x for _y in _GRID_VALS for x in _GRID_VALS]
_GY = [y for y in _GRID_VALS for _x in _GRID_VALS]

QUAD_COLORS = {"tl": "#4f6d5a", "tr": "#a8532f", "bl": "#6b7270", "br": "#c98a2c"}
QUAD_LABELS = {
    "tl": "Low AI · Removes Drudgery",
    "tr": "High AI · Removes Drudgery",
    "bl": "Low AI · Removes Judgment",
    "br": "High AI · Removes Judgment",
}
PAPER = "#f6f2e9"
INK = "#1c2b2d"
LINE = "#d8cfb8"


def quad_of(x: float, y: float) -> str:
    if x < 50 and y < 50:
        return "tl"
    if x >= 50 and y < 50:
        return "tr"
    if x < 50 and y >= 50:
        return "bl"
    return "br"


def build_map_figure(notes: list[dict]) -> go.Figure:
    fig = go.Figure()

    # Invisible dense grid — the actual click-capture surface.
    fig.add_trace(go.Scatter(
        x=_GX, y=_GY, mode="markers",
        marker=dict(size=30, color="rgba(0,0,0,0.01)"),
        hoverinfo="none", showlegend=False, name="_grid",
    ))

    for q in ("tl", "tr", "bl", "br"):
        subset = [n for n in notes if quad_of(n["x"], n["y"]) == q]
        fig.add_trace(go.Scatter(
            x=[n["x"] for n in subset],
            y=[n["y"] for n in subset],
            mode="markers",
            marker=dict(size=12, color=QUAD_COLORS[q], line=dict(width=1, color=INK)),
            name=QUAD_LABELS[q],
            hovertext=[n["text"] for n in subset],
            hoverinfo="text",
            showlegend=bool(subset),
        ))

    corner_style = dict(showarrow=False, font=dict(size=9, color="#6b7270"), opacity=0.75)
    fig.add_annotation(x=2, y=3, xanchor="left", yanchor="top", text="LOW AI · DRUDGERY", **corner_style)
    fig.add_annotation(x=98, y=3, xanchor="right", yanchor="top", text="HIGH AI · DRUDGERY", **corner_style)
    fig.add_annotation(x=2, y=97, xanchor="left", yanchor="bottom", text="LOW AI · JUDGMENT", **corner_style)
    fig.add_annotation(x=98, y=97, xanchor="right", yanchor="bottom", text="HIGH AI · JUDGMENT", **corner_style)

    fig.add_shape(type="line", x0=50, x1=50, y0=0, y1=100, line=dict(color=LINE, width=2))
    fig.add_shape(type="line", x0=0, x1=100, y0=50, y1=50, line=dict(color=LINE, width=2))

    fig.update_layout(
        xaxis=dict(
            range=[0, 100], showgrid=False, zeroline=False, fixedrange=True,
            showticklabels=False, title=dict(text="← Low AI involvement · · · High AI involvement →", font=dict(size=11)),
        ),
        yaxis=dict(
            range=[100, 0], showgrid=False, zeroline=False, fixedrange=True,
            showticklabels=False, title=dict(text="Removes drudgery ← · · → Removes judgment", font=dict(size=11)),
        ),
        height=440,
        margin=dict(l=10, r=10, t=40, b=40),
        plot_bgcolor=PAPER,
        paper_bgcolor=PAPER,
        font=dict(family="Courier New, monospace", color=INK, size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, font=dict(size=9.5)),
        clickmode="event+select",
        dragmode=False,
    )
    return fig
