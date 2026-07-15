# F1 Pit Wall Dashboard 🏎️

A professional-grade Formula 1 data analysis dashboard powered by **FastF1**, **Streamlit**, and **Plotly**.

## Features

- **🗺️ Track Analysis:** Visualize the circuit layout with integrated braking zones (Red) and full-throttle sections (Green). Includes official corner labeling.
- **📈 Telemetry Comparison:** Compare car performance parameters (Speed, Throttle, Brake, Gear, RPM) between multiple drivers over a single lap.
- **⏱️ Delta-T Analysis:** See exactly where a driver is gaining or losing time relative to another using interactive time-delta charts.
- **🎥 Race Replay:** Scrub through the entire session time to visualize real-time driver positions on the track map.
- **📊 Session Summary:** Get quick insights into session results and tyre strategies (stint lengths and compounds).

## Quick Start

The easiest way to run the dashboard is using the provided runner script:

```bash
./run_dashboard.sh
```

Alternatively, if you have the environment activated:

```bash
streamlit run src/f1dash/dashboard.py
```

## Dashboard Overview

1. **Session Selection:** Use the sidebar to pick the Season (2018-present), the Event (Grand Prix), and the specific Session (FP, Qualifying, Race).
2. **Driver Selection:** Select one or more drivers to compare their telemetry and track positions.
3. **Tabs:**
   - **Track Analysis:** Focused view of the circuit and driving inputs.
   - **Telemetry Comparison:** Line traces for deep technical analysis.
   - **Delta-T:** Comparative timing performance.
   - **Race Replay:** Dynamic position map.
   - **Session Summary:** Results and strategy overview.

## Data Source

All data is fetched from the official F1 live timing and Ergast API via the [FastF1](https://github.com/theOehrly/Fast-F1) library. Data for a live session typically becomes available 30-60 minutes after the session concludes.

---
*Developed for the F1 Pit Wall experience.*
# f1dash
# f1dash
# f1dash
