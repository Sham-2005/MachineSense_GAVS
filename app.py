"""MachineSense: an offline-first predictive maintenance demo (simulated data)."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from simulator import MACHINES, SENSORS, generate_history, next_reading
from model import train_models, score_reading
from agent import make_story
from notify import message, make_audio, rank_technicians

ROOT = Path(__file__).parent
DATA = ROOT / "data"
st.set_page_config(page_title="MachineSense", page_icon="⚙️", layout="wide")
st.title("⚙️ MachineSense")
st.caption("Offline-first machine health demo · Simulated sensor data · Prototype, not a safety system")

def initialize():
    if "histories" not in st.session_state:
        st.session_state.histories = {m: generate_history(m) for m in MACHINES}
        st.session_state.faults = {m: 0 for m in MACHINES}
        st.session_state.dusty = {m: False for m in MACHINES}
        st.session_state.models = train_models(st.session_state.histories)
        st.session_state.feedback = []
        st.session_state.approved = set()
        st.session_state.dispatch = {}
        st.session_state.dispatch_index = {}
        st.session_state.labels = 0
        st.session_state.threshold_bias = 0.0
    if "repairs" not in st.session_state:
        p = DATA / "repair_log.csv"
        st.session_state.repairs = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["date","machine","symptom","cause","part","cost_inr","downtime_days"])
initialize()

def add_day(machine):
    frame = st.session_state.histories[machine]
    row = next_reading(machine, frame, st.session_state.faults[machine], st.session_state.dusty[machine])
    st.session_state.histories[machine] = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
    # Fault is a one-time injection which continues drifting for the next 12 simulated days.
    if st.session_state.faults[machine] > 0:
        st.session_state.faults[machine] += 1

with st.sidebar:
    st.header("Demo controls")
    machine = st.selectbox("Selected machine", list(MACHINES))
    language = st.selectbox("Alert language", ["English", "Tamil", "Hindi"])
    if st.button("Inject bearing fault", use_container_width=True):
        st.session_state.faults[machine] = 1
        st.success("Bearing wear pattern injected")
    if st.button("Inject dust condition", use_container_width=True):
        st.session_state.dusty[machine] = True
        st.success("High dust injected")
    if st.button("Simulate next day", type="primary", use_container_width=True):
        add_day(machine)
    if st.button("Reset demo data", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    st.caption("Fault and dust toggles persist until reset. Simulation does not control equipment.")

tabs = st.tabs(["Live health", "Dispatch", "Repair & learning", "Impact"])
frame = st.session_state.histories[machine]
row = frame.iloc[-1].to_dict()
result = score_reading(machine, row, st.session_state.models, st.session_state.threshold_bias)
story = make_story(machine, result, row, st.session_state.repairs)

with tabs[0]:
    cols = st.columns(4)
    labels = [("Vibration", "vibration", "mm/s"), ("Temperature", "temperature", "°C"), ("Motor current", "current", "A"), ("Dust / PM2.5", "dust", "µg/m³")]
    for c, (label, key, unit) in zip(cols, labels):
        c.metric(label, f"{row[key]:.1f} {unit}", f"{result['deviations'][key]:+.0f}% vs baseline")
    dust = row["dust"]
    dust_state = "Dirty" if dust > 65 else "Moderate" if dust > 35 else "Clean"
    st.info(f"Environment: **{dust_state}** · Latest dust reading {dust:.1f} µg/m³. Dust is a risk factor; it does not prove the cause of a fault.")
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader(f"{machine} · Sensor history")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=frame.date, y=frame.vibration, name="Vibration", mode="lines+markers"))
        fig.add_trace(go.Scatter(x=frame.date, y=frame.temperature, name="Temperature", mode="lines+markers", yaxis="y2"))
        alerts = frame.iloc[30:].copy()
        if len(alerts):
            fig.add_trace(go.Scatter(x=alerts.loc[alerts.fault, "date"], y=alerts.loc[alerts.fault, "vibration"], name="Injected fault", mode="markers", marker={"color":"red", "size":11, "symbol":"x"}))
        fig.update_layout(height=330, margin={"t":20,"b":15}, yaxis={"title":"Vibration"}, yaxis2={"title":"Temperature °C", "overlaying":"y", "side":"right"}, legend={"orientation":"h"})
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Status & agent story")
        st.metric("Health status", result["status"], f"Anomaly score {result['anomaly_score']:.2f} · {result['confidence']} confidence")
        st.info(story)
        st.markdown("**Workflow:** 1 Detect → 2 Explain → 3 Plan → 4 Owner approval → 5 Notify → 6 Learn")
        if result["status"] != "Normal":
            a, b = st.columns(2)
            if a.button("Approve dispatch", type="primary", key=f"approve_{machine}"):
                st.session_state.approved.add(machine)
                st.session_state.dispatch_index[machine] = 0
                technicians = pd.read_csv(DATA / "technicians.csv")
                candidates = rank_technicians(technicians, "bearing" if result["sensor"] == "vibration" else result["sensor"], MACHINES[machine]["location"])
                st.session_state.dispatch[machine] = candidates.to_dict("records")
                st.rerun()
            if b.button("Ignore alert", key=f"ignore_{machine}"):
                st.session_state.approved.discard(machine)
                st.session_state.feedback.append("ignored")
                st.toast("Alert ignored; equipment state unchanged.")
        fb1, fb2 = st.columns(2)
        if fb1.button("Yes, I heard noise", key=f"noise_{machine}"):
            st.session_state.feedback.append("confirmed"); st.session_state.labels += 1
            st.session_state.threshold_bias = max(-.16, st.session_state.threshold_bias - .01)
        if fb2.button("False alarm", key=f"false_{machine}"):
            st.session_state.feedback.append("false_alarm"); st.session_state.labels += 1
            st.session_state.threshold_bias = min(.16, st.session_state.threshold_bias + .02)
        st.caption("Owner makes the decision. MachineSense never stops a machine.")

with tabs[1]:
    st.subheader("Owner-approved technician & parts dispatch")
    if machine not in st.session_state.approved:
        st.caption("Approve a non-normal alert in Live health to start the simulated dispatch.")
    elif machine not in st.session_state.dispatch:
        st.caption("Dispatch is being prepared.")
    else:
        techs = st.session_state.dispatch[machine]
        i = st.session_state.dispatch_index.get(machine, 0)
        if i >= len(techs):
            st.error("No technician accepted. Owner can retry or arrange service manually.")
        else:
            tech = techs[i]
            part = "bearing" if result["sensor"] == "vibration" else "vent filter" if result["sensor"] == "dust" else "motor belt"
            dealer_rows = pd.read_csv(DATA / "dealers.csv")
            dealer = dealer_rows[dealer_rows.part == part]
            if dealer.empty: dealer = dealer_rows.iloc[[0]]
            d = dealer.iloc[0]
            txt = message(machine, story, result["status"], part, MACHINES[machine]["location"], language)
            st.write(f"**Technician candidate {i+1}/{len(techs)}:** {tech['name']} · {tech['phone']} · {tech['skills']} · {tech['location']}")
            st.code(txt)
            audio = make_audio(txt, language)
            if audio: st.audio(audio)
            else: st.caption("Voice unavailable offline or gTTS not installed; text alert remains available.")
            st.success(f"Dealer message prepared: {d.dealer} · {part} · stock {d.stock} · ₹{d.price_inr} · {d.phone}")
            st.write("**Simulated technician response**")
            c1, c2 = st.columns(2)
            if c1.button("Accept", key=f"accept_{machine}_{i}"):
                st.session_state.dispatch[machine][i]["response"] = "Accepted"
                st.success(f"{tech['name']} accepted. Suggested slot: Sunday 2 pm–6 pm.")
            if c2.button("Decline", key=f"decline_{machine}_{i}"):
                st.session_state.dispatch_index[machine] = i + 1
                st.rerun()
            if tech.get("response") == "Accepted": st.success("Technician accepted · owner may record the completed repair in Repair & learning.")

with tabs[2]:
    st.subheader("Repair log")
    with st.form("repair_form"):
        c1,c2,c3 = st.columns(3)
        symptom = c1.text_input("Observed symptom", value=(f"{result['sensor']} elevated" if result["status"] != "Normal" else "routine service"))
        cause = c2.selectbox("Confirmed cause", ["bearing wear", "dust buildup", "electrical", "other / unknown"])
        part = c3.text_input("Part replaced", value="bearing" if cause == "bearing wear" else "")
        c4,c5,c6 = st.columns(3)
        cost = c4.number_input("Repair cost (₹)", min_value=0, value=850, step=100)
        downtime = c5.number_input("Downtime (days)", min_value=0.0, value=1.0, step=0.5)
        save = st.form_submit_button("Save completed repair")
    if save:
        record = {"date":pd.Timestamp.now().date().isoformat(), "machine":machine, "symptom":symptom, "cause":cause, "part":part, "cost_inr":cost, "downtime_days":downtime}
        st.session_state.repairs = pd.concat([st.session_state.repairs, pd.DataFrame([record])], ignore_index=True)
        st.session_state.repairs.to_csv(DATA / "repair_log.csv", index=False)
        st.session_state.labels += 1
        st.success("Repair saved locally. This becomes a labeled example for future stories.")
    st.dataframe(st.session_state.repairs, use_container_width=True, hide_index=True)
    st.subheader("Learning loop")
    st.progress(min(st.session_state.labels / 10, 1.0), text=f"Stage 2: Semi-supervised · {st.session_state.labels} labels collected (Stage 1: Unsupervised → Stage 2: Semi-supervised)")
    st.caption(f"Feedback and repairs are stored locally and inform similar-case stories. Feedback nudges the alert threshold (current adjustment {st.session_state.threshold_bias:+.2f}); the Isolation Forest remains the unsupervised base model.")

with tabs[3]:
    st.subheader("Estimated impact")
    col1,col2 = st.columns(2)
    daily_loss = col1.number_input("Estimated loss per downtime day (₹)", min_value=0, value=10000, step=1000)
    avoided = col2.number_input("Estimated avoided downtime (days)", min_value=0.0, value=2.0, step=0.5)
    st.metric("Estimated money saved", f"₹{daily_loss*avoided:,.0f}", help="User-provided estimate; not measured savings.")
    timeline = pd.DataFrame({"Phase":["Before MachineSense", "With MachineSense"], "Downtime days": [5, max(0, 5-avoided)]})
    chart = go.Figure(go.Bar(x=timeline.Phase, y=timeline["Downtime days"], marker_color=["#c75b39", "#218c74"], text=timeline["Downtime days"], textposition="outside"))
    chart.update_layout(height=280, yaxis_title="Illustrative downtime days", margin={"t":10,"b":10})
    st.plotly_chart(chart, use_container_width=True)
    st.caption("Before/after figures are illustrative inputs for a hackathon demo, not measured results.")
