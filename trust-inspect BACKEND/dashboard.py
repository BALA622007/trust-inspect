import requests
import pandas as pd
import streamlit as st

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="TRUST-Inspect", layout="wide")
st.title("🤖 TRUST-Inspect — Explainable AI Monitoring POC")
st.caption("SIH26095 prototype: AI risk + evidence provenance + audit ledger")

try:
    projects = requests.get(f"{API}/projects", timeout=3).json()
except Exception:
    st.error("Start the API first: uvicorn app.main:app --reload")
    st.stop()

df = pd.DataFrame(projects)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Projects", len(df))
c2.metric("High Risk", int((df["risk_score"] >= 65).sum()) if len(df) else 0)
c3.metric("Medium Risk", int(((df["risk_score"] >= 35) & (df["risk_score"] < 65)).sum()) if len(df) else 0)
c4.metric("Low Risk", int((df["risk_score"] < 35).sum()) if len(df) else 0)

st.subheader("Project Risk Board")
if len(df):
    st.dataframe(df, use_container_width=True)

st.subheader("Run Explainable AI")
if len(df):
    selected = st.selectbox("Project", df["id"].tolist(), format_func=lambda x: f"Project {x}: {df.loc[df.id==x, 'name'].iloc[0]}")
    if st.button("Analyze Project"):
        result = requests.post(f"{API}/ai/analyze/{selected}", timeout=10).json()
        st.json(result)

        st.markdown("### Decision")
        st.write(f"**Risk:** {result['risk_score']}/100 — **{result['risk_level']}**")
        st.write(f"**Confidence:** {result['confidence']*100:.0f}%")
        st.write(f"**Recommendation:** `{result['recommendation']}`")

        st.markdown("### Why?")
        for r in result["reasons"]:
            st.write(f"- **{r['feature']}** — signal={r['value']:.2f}, contribution=+{r['contribution']:.2f}")

st.subheader("Ledger Integrity")
if st.button("Verify Ledger"):
    st.json(requests.get(f"{API}/ledger/verify", timeout=10).json())

st.subheader("Assign Surprise Inspection")
if st.button("Run Assignment Engine"):
    st.json(requests.post(f"{API}/inspections/assign", timeout=10).json())

st.subheader("Audit Trail")
if st.button("Refresh Audit Logs"):
    st.dataframe(pd.DataFrame(requests.get(f"{API}/audit", timeout=10).json()), use_container_width=True)
