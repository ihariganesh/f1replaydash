import streamlit as st
import fastf1
import fastf1.plotting
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import time
from pathlib import Path

# Setup FastF1
CACHE_DIR = Path("/home/hari/f1dash/.cache/fastf1")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

# Initialise Session State
if 'is_playing' not in st.session_state: st.session_state.is_playing = False
if 'replay_time' not in st.session_state: st.session_state.replay_time = 0
if 'playback_speed' not in st.session_state: st.session_state.playback_speed = 1.0
if 'is_playing_tel' not in st.session_state: st.session_state.is_playing_tel = False
if 'tel_distance' not in st.session_state: st.session_state.tel_distance = 0.0
if 'playback_speed_tel' not in st.session_state: st.session_state.playback_speed_tel = 1.0
if 'replay_lap' not in st.session_state: st.session_state.replay_lap = 1
if 'sync_laps' not in st.session_state: st.session_state.sync_laps = True

# Page Config
st.set_page_config(page_title="F1 Pit Wall Dashboard Pro", layout="wide", page_icon="🏎️")

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #fafafa; }
    div[data-testid="stMetric"] {
        background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3d4455;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #1e2130; border-radius: 4px 4px 0px 0px; padding: 10px;
    }
    .stTabs [aria-selected="true"] { background-color: #3d4455; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏎️ F1 Pit Wall Dashboard Pro")

# --- Sidebar Controls ---
st.sidebar.header("Session Selection")
year_sel = st.sidebar.selectbox("Season", list(range(2026, 2017, -1)), index=0)

@st.cache_data
def get_events(year):
    schedule = fastf1.get_event_schedule(year)
    return schedule[['RoundNumber', 'EventName']].values.tolist()

events = get_events(year_sel)
selected_event_str = st.sidebar.selectbox("Event", [f"R{r}: {n}" for r, n in events])
round_number = int(selected_event_str.split(":")[0][1:])
session_type = st.sidebar.selectbox("Session", ["FP1", "FP2", "FP3", "Qualifying", "Sprint", "Race"], index=5)

# --- Data Loading ---
@st.cache_resource
def load_session_data(year, round_num, s_type):
    try:
        session = fastf1.get_session(year, round_num, s_type)
        session.load(laps=True, telemetry=True, weather=True)
        return session
    except: return None

@st.cache_resource
def get_session_metadata(_session):
    """Extracts track features like DRS, Sectors, and Layout once per session."""
    track_layout, drs_zones, drs_detection_points, sector_points = None, [], [], {}
    try:
        fastest_lap = _session.laps.pick_fastest()
        ref_tel = fastest_lap.get_telemetry().add_distance()
        track_layout = {'X': ref_tel['X'].tolist(), 'Y': ref_tel['Y'].tolist()}
        
        # --- Sector Boundaries ---
        try:
            s1_time = fastest_lap['Sector1SessionTime']
            s2_time = fastest_lap['Sector2SessionTime']
            s1_idx = (ref_tel['Time'] - s1_time).abs().idxmin()
            s2_idx = (ref_tel['Time'] - s2_time).abs().idxmin()
            sector_points['S1'] = {'X': ref_tel.loc[s1_idx, 'X'], 'Y': ref_tel.loc[s1_idx, 'Y']}
            sector_points['S2'] = {'X': ref_tel.loc[s2_idx, 'X'], 'Y': ref_tel.loc[s2_idx, 'Y']}
        except: pass

        # --- DRS/Active Aero ---
        target_laps = [fastest_lap]
        if len(_session.laps) > 5:
            target_laps.extend([_session.laps.loc[i] for i in _session.laps.sort_values('LapTime').head(5).index])
        
        for lap in target_laps:
            l_tel = lap.get_telemetry().add_distance()
            if (l_tel['DRS'] >= 10).any():
                l_tel['A_Active'] = l_tel['DRS'] >= 10
                l_tel['A_Grp'] = (l_tel['A_Active'] != l_tel['A_Active'].shift()).cumsum()
                for _, group in l_tel[l_tel['A_Active']].groupby('A_Grp'):
                    if len(group) > 2: drs_zones.append({'X': group['X'].tolist(), 'Y': group['Y'].tolist()})
                
                det_pulse = (l_tel['DRS'] == 8)
                if det_pulse.any():
                    l_tel['D_Grp'] = (det_pulse != det_pulse.shift()).cumsum()
                    dets = l_tel[det_pulse].groupby('D_Grp').first()
                    for _, row in dets.iterrows(): drs_detection_points.append({'X': row['X'], 'Y': row['Y']})
                break
    except: pass
    return track_layout, drs_zones, drs_detection_points, sector_points

@st.cache_data
def get_lap_telemetry(_session, driver_codes, lap_number):
    """Loads telemetry only for a specific lap and set of drivers."""
    lap_data = {}
    for code in driver_codes:
        try:
            lap = _session.laps.pick_drivers(code).pick_lap(lap_number)
            tel = lap.get_telemetry().add_distance()
            lap_data[code] = tel
        except: continue
    return lap_data

def add_track_annotations(fig, session, year, drs_zones, drs_dets, sector_points):
    """Draws DRS zones, detection points, corner numbers, and sectors."""
    label = "Active Aero" if year >= 2026 else "DRS"
    
    # 1. DRS/Aero Zones
    for i, zone in enumerate(drs_zones):
        try:
            x, y = np.array(zone['X']), np.array(zone['Y'])
            dx, dy = np.gradient(x), np.gradient(y)
            mag = np.sqrt(dx**2 + dy**2); mag[mag == 0] = 1.0
            nx, ny = -dy / mag, dx / mag
            offset = 200
            x_off, y_off = x + nx * offset, y + ny * offset
            
            fig.add_trace(go.Scatter(x=x_off, y=y_off, mode='lines', line=dict(color='#00ff00', width=5), name=f'{label} Zone {i+1}', showlegend=False, hoverinfo='text', hovertext=f'{label} Zone {i+1}'))
            mid = len(x_off) // 2
            fig.add_annotation(x=x_off[mid], y=y_off[mid], text=f"ZONE {i+1}", showarrow=False, font=dict(color="#00ff00", size=11, family="Arial Black"), bgcolor="rgba(0,0,0,0.7)", bordercolor="#00ff00", borderwidth=1, borderpad=2)
        except: continue

    # 2. Detection Points
    for det in drs_dets:
        fig.add_trace(go.Scatter(x=[det['X']], y=[det['Y']], mode='markers', marker=dict(color='yellow', size=12, symbol='diamond', line=dict(color='black', width=1.5)), name='Detection', hoverinfo='text', hovertext=f"{label} Detection Point", showlegend=False))

    # 3. Corner Numbers
    try:
        circuit_info = session.get_circuit_info()
        for _, corner in circuit_info.corners.iterrows():
            fig.add_annotation(x=corner['X'], y=corner['Y'], text=str(corner['Number']), showarrow=False, font=dict(color="white", size=12, family="Arial Black"), bgcolor="black", opacity=0.8, bordercolor="white", borderwidth=1, borderpad=2)
    except: pass

    # 4. Sector Markers
    for s_name, pt in sector_points.items():
        fig.add_trace(go.Scatter(
            x=[pt['X']], y=[pt['Y']], 
            mode='markers+text', 
            text=[s_name], 
            textposition="middle center", 
            marker=dict(color='white', size=25, symbol='circle-open', line=dict(width=2)), 
            textfont=dict(color="white", size=14, family="Arial Black"), 
            name=f"Sector Boundary", 
            showlegend=False
        ))

@st.cache_data
def get_driver_positions_v2(_session, driver_codes):
    """Loads raw position data (X, Y) for the whole session efficiently."""
    positions = {}
    for code in driver_codes:
        try:
            pos = _session.laps.pick_drivers(code).get_pos_data()
            if 'Time' in pos.columns and 'X' in pos.columns and 'Y' in pos.columns:
                positions[code] = pos[['Time', 'X', 'Y']]
            else:
                print(f"Missing columns in pos data for {code}: {pos.columns}")
        except Exception as e:
            print(f"Failed to load pos data for {code}: {e}")
            continue
    return positions

session = load_session_data(year_sel, round_number, session_type)

if session:
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Event", session.event['EventName'])
    with m2: st.metric("Session", session.name)
    with m3: st.metric("Track Temp", f"{session.weather_data['TrackTemp'].mean():.1f}°C" if not session.weather_data.empty else "N/A")
    with m4: st.metric("Air Temp", f"{session.weather_data['AirTemp'].mean():.1f}°C" if not session.weather_data.empty else "N/A")

    st.sidebar.success(f"Loaded: {session.event['EventName']} - {session.name}")
    
    # Selection
    drivers = session.drivers
    driver_infos = [{'code': session.get_driver(d)['Abbreviation'], 'color': session.get_driver(d)['TeamColor']} for d in drivers]
    driver_df = pd.DataFrame(driver_infos)
    st.sidebar.header("Driver & Lap Selection")
    selected_drivers = st.sidebar.multiselect("Drivers (up to 4)", options=driver_df['code'].tolist(), default=driver_df['code'].iloc[:2].tolist())
    
    driver_lookup = {row['code']: row['color'] for _, row in driver_df.iterrows()}
    
    st.sidebar.header("Global Replay Controls")
    st.session_state.sync_laps = st.sidebar.checkbox("Sync Drivers to Global Lap", value=st.session_state.sync_laps)
    max_laps = int(session.laps['LapNumber'].max())
    st.session_state.replay_lap = st.sidebar.slider("Global Lap", 1, max_laps, int(st.session_state.replay_lap))

    selected_laps = {}
    for d_code in selected_drivers:
        d_laps = session.laps.pick_drivers(d_code).sort_values('LapNumber')
        if not d_laps.empty:
            if st.session_state.sync_laps:
                selected_laps[d_code] = d_laps[d_laps['LapNumber'] == st.session_state.replay_lap].iloc[0] if not d_laps[d_laps['LapNumber'] == st.session_state.replay_lap].empty else d_laps.pick_fastest()
            else:
                sel_lap = st.sidebar.selectbox(f"Lap for {d_code}", options=["Fastest"] + d_laps['LapNumber'].astype(int).tolist(), key=f"lap_sel_{d_code}")
                selected_laps[d_code] = d_laps.pick_fastest() if sel_lap == "Fastest" else d_laps[d_laps['LapNumber'] == sel_lap].iloc[0]

    if selected_drivers:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Split-View Track Analysis", "📈 Telemetry Comparison", "⏱️ Delta & Heatmaps", "🎥 Race Replay", "📊 Session Summary"])
        track_layout, drs_zones, drs_dets, sector_pts = get_session_metadata(session)

        with tab1:
            st.header("Comparative Track Analysis")
            cols = st.columns(2)
            for i, d_code in enumerate(selected_drivers):
                with cols[i % 2]:
                    lap = selected_laps.get(d_code)
                    if lap is not None:
                        tel = lap.get_telemetry().add_distance()
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=tel['X'], y=tel['Y'], mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=2), name='Track', hoverinfo='skip'))
                        add_track_annotations(fig, session, year_sel, drs_zones, drs_dets, sector_pts)
                        braking, throttle = tel[tel['Brake'] > 0], tel[tel['Throttle'] > 95]
                        fig.add_trace(go.Scatter(x=braking['X'], y=braking['Y'], mode='markers', marker=dict(color='red', size=5), name='Brake'))
                        fig.add_trace(go.Scatter(x=throttle['X'], y=throttle['Y'], mode='markers', marker=dict(color='#00ff00', size=4), name='Throttle'))
                        fig.update_layout(template="plotly_dark", height=500, title=f"{d_code} - Lap {int(lap['LapNumber'])}", xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.header(f"Detailed Telemetry Comparison - Lap {st.session_state.replay_lap if st.session_state.sync_laps else 'Selected'}")
            # Use cached lap telemetry for efficiency
            tele_data = {}
            for d in selected_drivers:
                if d in selected_laps:
                    lap_num = int(selected_laps[d]['LapNumber'])
                    # Only load if needed
                    tel = get_lap_telemetry(session, [d], lap_num).get(d)
                    if tel is not None:
                        tele_data[d] = (tel, "#"+driver_lookup[d])

            if tele_data:
                max_d = max([t[0]['Distance'].max() for t in tele_data.values()])
                t1, t2 = st.columns([1, 4])
                with t1:
                    if st.session_state.is_playing_tel:
                        if st.button("⏸️ Pause", key="tp"): st.session_state.is_playing_tel = False; st.rerun()
                    else:
                        if st.button("▶️ Play", key="tpl"): st.session_state.is_playing_tel = True; st.rerun()
                    if st.button("⏹️ Stop", key="ts"): st.session_state.is_playing_tel = False; st.session_state.tel_distance = 0.0; st.rerun()
                with t2: st.session_state.tel_distance = st.slider("Distance Scrubber", 0.0, float(max_d), float(st.session_state.tel_distance), step=25.0)
                
                c_map, c_plot = st.columns([1, 2])
                with c_map:
                    fig_l = go.Figure()
                    ref_t = list(tele_data.values())[0][0]
                    fig_l.add_trace(go.Scatter(x=ref_t['X'], y=ref_t['Y'], mode='lines', line=dict(color='rgba(255,255,255,0.2)', width=2), hoverinfo='skip'))
                    add_track_annotations(fig_l, session, year_sel, drs_zones, drs_dets, sector_pts)
                    for d, (tel, color) in tele_data.items():
                        pt = tel.loc[(tel['Distance'] - st.session_state.tel_distance).abs().idxmin()]
                        fig_l.add_trace(go.Scatter(x=[pt['X']], y=[pt['Y']], mode='markers', marker=dict(color=color, size=15, symbol='cross', line=dict(color='white', width=2)), name=d))
                    fig_l.update_layout(template="plotly_dark", height=600, xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig_l, use_container_width=True)
                with c_plot:
                    for ch in ['Speed', 'Throttle', 'Brake']:
                        fig = go.Figure()
                        for d, (tel, color) in tele_data.items():
                            fig.add_trace(go.Scatter(x=tel['Distance'], y=tel[ch], mode='lines', name=d, line=dict(color=color, width=2)))
                        fig.add_vline(x=st.session_state.tel_distance, line_width=2, line_color="white")
                        fig.update_layout(template="plotly_dark", height=200, title=ch, margin=dict(l=0, r=0, t=30, b=0), showlegend=(ch=='Speed'))
                        st.plotly_chart(fig, use_container_width=True)
                if st.session_state.is_playing_tel:
                    st.session_state.tel_distance = min(max_d, st.session_state.tel_distance + 150 * st.session_state.playback_speed_tel)
                    if st.session_state.tel_distance >= max_d: 
                        if st.session_state.sync_laps and st.session_state.replay_lap < max_laps:
                            st.session_state.replay_lap += 1
                            st.session_state.tel_distance = 0.0
                        else:
                            st.session_state.is_playing_tel = False
                    time.sleep(0.05); st.rerun()

        with tab3:
            st.header("Speed Heatmaps")
            if len(selected_drivers) >= 2:
                d1, d2 = selected_drivers[0], selected_drivers[1]
                t1, t2 = selected_laps[d1].get_telemetry().add_distance(), selected_laps[d2].get_telemetry().add_distance()
                delta = t1['Speed'] - np.interp(t1['Distance'], t2['Distance'], t2['Speed'])
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=t1['X'], y=t1['Y'], mode='lines', line=dict(color='rgba(255,255,255,0.1)', width=2), hoverinfo='skip'))
                add_track_annotations(fig, session, year_sel, drs_zones, drs_dets, sector_pts)
                fig.add_trace(go.Scatter(x=t1['X'], y=t1['Y'], mode='markers', marker=dict(size=5, color=delta, colorscale='RdBu', reversescale=True, cmid=0, colorbar=dict(title="km/h")), name="Speed Delta"))
                fig.update_layout(template="plotly_dark", height=750, xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), title=f"Speed Delta: {d1} vs {d2}")
                st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.header("🎥 Continuous Race Replay (Smooth)")
            
            # Use raw session positions for full replay
            session_positions = get_driver_positions_v2(session, selected_drivers)
            
            if session_positions:
                # 1. Downsample for Plotly Animation (Plotly struggles with 100k points)
                # We'll take one point every 2 seconds for a "summary" replay that is smooth
                all_times = [p['Time'].max().total_seconds() for p in session_positions.values()]
                total_seconds = int(max(all_times)) if all_times else 3600
                
                # Create a fixed timeline for animation
                step = 2.0  # seconds per frame
                timeline = np.arange(0, total_seconds, step)
                
                # Build frames for Plotly
                frames = []
                for t in timeline:
                    target_td = pd.Timedelta(seconds=t)
                    frame_data = []
                    for d in selected_drivers:
                        try:
                            p = session_positions[d]
                            # Find nearest point
                            row = p.loc[(p['Time'] - target_td).abs().idxmin()]
                            frame_data.append(go.Scatter(
                                x=[row['X']], y=[row['Y']],
                                mode='markers+text',
                                marker=dict(color="#"+driver_lookup[d], size=14, line=dict(color='white', width=1)),
                                text=[d], textposition="top center", name=d
                            ))
                        except: continue
                    frames.append(go.Frame(data=frame_data, name=str(int(t))))

                # Create Base Figure
                fig_anim = go.Figure(
                    data=[go.Scatter(x=track_layout['X'], y=track_layout['Y'], mode='lines', line=dict(color='rgba(255,255,255,0.1)', width=2), hoverinfo='skip')] if track_layout else [],
                    layout=go.Layout(
                        template="plotly_dark", height=800,
                        xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
                        showlegend=False, margin=dict(l=0, r=0, t=0, b=0),
                        updatemenus=[dict(
                            type="buttons", showactive=False,
                            buttons=[
                                dict(label="▶ Play", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True)]),
                                dict(label="⏸ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])
                            ]
                        )],
                        sliders=[dict(
                            steps=[dict(method="animate", args=[[str(int(t))], dict(mode="immediate", frame=dict(duration=100, redraw=True))], label=f"{int(t//60)}m") for t in timeline],
                            transition=dict(duration=0), x=0, y=0, currentvalue=dict(font=dict(size=12), prefix="Session Time: ", visible=True, xanchor="right")
                        )]
                    ),
                    frames=frames
                )
                
                # Add track features to base figure
                add_track_annotations(fig_anim, session, year_sel, drs_zones, drs_dets, sector_pts)
                
                st.plotly_chart(fig_anim, use_container_width=True)
                st.info("This replay runs entirely in your browser using Plotly's animation engine. Press 'Play' above to start.")
            else:
                st.warning("No position data available. Try selecting different drivers or ensuring the session is fully loaded.")

        with tab5:
            st.header("Session Summary")
            c1, c2 = st.columns(2)
            with c1: st.subheader("Results"); st.dataframe(session.results[['Abbreviation', 'TeamName', 'ClassifiedPosition', 'Status']], use_container_width=True)
            with c2:
                st.subheader("Tyre Strategy")
                stints = session.laps[['Driver', 'Stint', 'Compound', 'LapNumber']].groupby(['Driver', 'Stint']).agg({'Compound': 'first', 'LapNumber': 'count'}).reset_index()
                st.plotly_chart(px.bar(stints, x="Driver", y="LapNumber", color="Compound", template="plotly_dark", color_discrete_map={'SOFT': 'red', 'MEDIUM': 'yellow', 'HARD': 'white', 'INTERMEDIATE': 'green', 'WET': 'blue'}), use_container_width=True)
    else: st.info("Select drivers in the sidebar.")
else: st.info("Select a session in the sidebar.")
