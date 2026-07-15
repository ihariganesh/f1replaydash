# 🏎️ F1 Pit Wall Dashboard Pro

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.0+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57+-FF4B4B.svg?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF.svg?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)

A dual-interface, professional-grade Formula 1 telemetry and race analysis pit wall dashboard. Powered by **FastF1**, **FastAPI**, **React (Vite)**, **Streamlit**, and **Plotly** to deliver a real-time data experience.

---

## 🌟 Features

### 🗺️ Track & Sector Analysis
- **Dynamic Speed Maps:** High-fidelity track layouts displaying full-throttle (Green) vs. braking zones (Red).
- ** DRS & Sector Analysis:** Interactive track visualization overlaying DRS activation zones and micro-sector timing deltas.

### 📈 Multi-Driver Telemetry Comparison
- **Driver Telemetry Traces:** Plot Speed, Throttle, Brake, Gear, RPM, and DRS overlays.
- **Delta-T Analysis:** Live time-difference charts to pinpoint exactly where one driver is gaining or losing time relative to another.

### 🎥 Interactive Race Replay
- **Replay Playback Control:** Play, pause, and adjust speed to replay driver positions moving dynamically across the track layout.

### 📊 Strategy & Summary
- **Tyre Stint Strategy:** Detailed visualizations of stint lengths, tyre compounds (Soft, Medium, Hard, Wet, Intermediate), and tyre degradation.
- **Pit Stop Analysis:** Overview of pit stop durations and execution times.

---

## 🛠️ Architecture

This repository offers two independent ways to view the data:

```
                  ┌──────────────────────────────────────────────┐
                  │                 FastF1 Data                  │
                  └──────────────────────┬───────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
       ┌───────────────────────┐                   ┌───────────────────────┐
       │   Streamlit App       │                   │   FastAPI Backend     │
       │   (Single-page Py)    │                   │   (REST APIs + Cache) │
       └───────────────────────┘                   └───────────┬───────────┘
                                                               │
                                                               ▼
                                                   ┌───────────────────────┐
                                                   │    React Frontend     │
                                                   │   (Vite + TS + CSS)   │
                                                   └───────────────────────┘
```

1. **Option A: Streamlit Standalone Dashboard:** Quick, powerful, interactive Python-native telemetry dashboard.
2. **Option B: Full-Stack React + FastAPI Web App:** Modern, state-of-the-art multi-view dashboard with a Python API backend.

---

## 🚀 Quick Start (Linux / macOS / Git Bash)

### 1. Setup Environment
Clone the repository and copy the environment template:
```bash
cp -n .env.example .env
```

### 2. Launch Streamlit (Option A)
To run the quick standalone Streamlit dashboard:
```bash
./run_dashboard.sh
```
*Access in browser at **http://localhost:8501***

### 3. Launch React + FastAPI (Option B)
Run the backend and frontend in separate terminals:

* **Terminal 1 (FastAPI Backend):**
  ```bash
  source .venv/bin/activate
  uvicorn f1dash.main:app --host 127.0.0.1 --port 8000 --reload
  ```
  *(Interactive Swagger API docs available at http://127.0.0.1:8000/docs)*

* **Terminal 2 (React Frontend):**
  ```bash
  cd frontend
  npm --prefix . run dev
  ```
  *Access the web app in browser at **http://localhost:5173***

---

## 💻 Quick Start (Windows PowerShell / Command Prompt)

### 1. Setup Environment
```powershell
copy .env.example .env
```

### 2. Launch Streamlit (Option A)
* **PowerShell:**
  ```powershell
  .venv\Scripts\Activate.ps1
  streamlit run src\f1dash\dashboard.py
  ```
* **Command Prompt:**
  ```cmd
  .venv\Scripts\activate.bat
  streamlit run src\f1dash\dashboard.py
  ```

### 3. Launch React + FastAPI (Option B)
* **Terminal 1 (FastAPI Backend):**
  ```powershell
  .venv\Scripts\Activate.ps1
  uvicorn f1dash.main:app --host 127.0.0.1 --port 8000 --reload
  ```
* **Terminal 2 (React Frontend):**
  ```powershell
  cd frontend
  npm --prefix . run dev
  ```

---

## 📊 Data Source & Caching
All telemetry, timing, and tyre compound data is fetched from the official F1 live timing and Ergast API via the [FastF1](https://github.com/theOehrly/Fast-F1) library.
- FastF1 downloads are cached locally in `.cache/fastf1/` to speed up subsequent queries.
- Precomputed session snapshots are exported to `exports/` to keep UI render times fast.
- Includes an optional Redis cache layer.
