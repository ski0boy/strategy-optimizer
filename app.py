import streamlit as st
import numpy as np
import pandas as pd
import random

# === CONFIG ===
account_tiers = {
    "50K": {"profit_target": 3000, "max_loss_limit": 2000},
    "100K": {"profit_target": 6000, "max_loss_limit": 3000},
    "150K": {"profit_target": 9000, "max_loss_limit": 4500},
}

# === MONTE-CARLO ENGINE ===

def simulate_one_run(win_rate: float, risk: float, rr: float, tpd: int, target: float, mll: float):
    """Simulate one evaluation until pass / fail and return dict."""
    balance = 0.0
    peak_balance = 0.0  # track equity highs for drawdown calc

    profit_days = []  # store P/L per winning day for consistency rule
    day = 0

    # ─── TRADING LOOP ──────────────────────────────────────────
    while balance < target and (peak_balance - balance) <= mll:
        day += 1
        day_pl = 0.0
        for _ in range(tpd):
            is_win = random.random() < win_rate
            result = risk * rr if is_win else -risk
            balance += result
            day_pl += result

            # update peak & drawdown
            peak_balance = max(peak_balance, balance)
            if (peak_balance - balance) > mll:
                return {"passed": False, "days": day, "reason": "drawdown"}
            if balance >= target:
                break  # stop early if target is met

        profit_days.append(day_pl)

    # ─── PASS / CONSISTENCY CHECK ─────────────────────────────
    if balance >= target:
        positive_days = [p for p in profit_days if p > 0]
        if len(positive_days) < 2:
            return {"passed": False, "days": day, "reason": "<2 profit days"}
        lowest_prof_day = min(positive_days)
        if lowest_prof_day < 0.5 * balance:  # 50% consistency rule
            return {"passed": False, "days": day, "reason": "consistency"}
        return {"passed": True, "days": day, "reason": "passed"}

    return {"passed": False, "days": day, "reason": "target_not_hit"}

# === STREAMLIT UI ===

st.title("📊 Topstep Combine Strategy Optimizer")

account = st.selectbox("Select Account Tier", list(account_tiers.keys()))
SIMS = st.slider("Number of Simulations", 100, 2000, 500, step=100)

col1, col2, col3 = st.columns(3)
with col1:
    win_rate = st.slider("Win Rate (%)", 35, 65, 55) / 100
with col2:
    risk_per_trade = st.slider("Risk per Trade ($)", 100, 2000, 300, step=100)
with col3:
    rr = st.slider("Risk:Reward Ratio", 1.0, 3.0, 2.0, step=0.5)

trades_per_day = st.slider("Trades per Day", 1, 10, 2)

if st.button("Run Simulation"):
    with st.spinner("Simulating…"):
        results = [simulate_one_run(win_rate, risk_per_trade, rr, trades_per_day,
                                    account_tiers[account]["profit_target"],
                                    account_tiers[account]["max_loss_limit"]) for _ in range(SIMS)]

        passes = [x for x in results if x["passed"]]
        pass_rate = round(len(passes) / SIMS * 100, 1)
        avg_days = round(np.mean([x["days"] for x in passes]), 1) if passes else None

        st.success(f"✅ Pass Rate: {pass_rate}%")
        if avg_days is not None:
            st.info(f"📆 Avg Days to Pass: {avg_days}")

        # Histogram of days to pass
        if passes:
            hist = pd.Series([x["days"] for x in passes]).value_counts().sort_index()
            st.bar_chart(hist)

        # Optional breakdown of fail reasons
        with st.expander("Show fail-reason breakdown"):
            fail_reasons = pd.Series([x["reason"] for x in results if not x["passed"]]).value_counts()
            st.write(fail_reasons)
