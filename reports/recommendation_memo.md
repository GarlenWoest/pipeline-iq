# Recommendation Memo — Pipeline IQ

**To:** VP, Sales
**From:** Revenue Analytics
**Re:** Where to concentrate selling capacity next quarter

---

## Summary

We analyzed **8,800 opportunities** ($20.9M closed-won) across 85 accounts and 30
reps. Win rate is **47.8%** overall but ranges from **58.3% (Technology)** to
**37.3% (Marketing)** — a 21-point spread that is not being reflected in how
prospecting effort is allocated. Three moves below are projected to lift blended
win rate and protect concentrated revenue.

## Finding 1 — Sector mix is diluting win rate

The win-driver model (logistic regression, cross-validated AUC 0.60) ranks
**sector** and **account tier** among the strongest predictors of a win.
Technology, Software, and Finance carry positive win-odds coefficients; Marketing
and Entertainment are negative.

**Recommendation:** shift ~15–20% of prospecting capacity out of the two
lowest-converting sectors into Technology/Software. At current volumes, moving
even 500 opportunities from a ~37% to a ~58% win rate is **~100 additional wins**.

## Finding 2 — Enterprise accounts convert materially better

Enterprise-tier accounts show a positive win-odds coefficient vs. a negative one
for SMB. Larger, structured buyers close more reliably despite longer cycles.

**Recommendation:** weight lead routing and senior-rep assignment toward
Enterprise and Mid-Market accounts; treat SMB as a velocity/volume play with
lighter-touch coverage.

## Finding 3 — Revenue is concentrated; protect the top tier

The top **20%** of accounts by won revenue drive **~27%** of all revenue. The
RFM + K-means segmentation isolates **22 "Strategic" accounts** (high frequency,
high value) that warrant named coverage and retention focus.

**Recommendation:** assign the 22 Strategic accounts named owners and a quarterly
business-review cadence; monitor the **At-Risk** tier (16 accounts) for churn
signals (rising recency, falling frequency).

## Forecast & quota

A walk-forward-backtested forecast (**20.1% MAPE**) projects **~$2.89M** in
bookings next quarter from historical trend, against **$0.79M** of weighted open
pipeline today. The gap implies **pipeline coverage is thin** for the target —
prioritize top-of-funnel generation in the high-converting sectors above to close
it.

## Suggested next steps

1. Re-route Q+1 prospecting toward Technology/Software + Enterprise tier.
2. Stand up named coverage for the 22 Strategic accounts.
3. Add an At-Risk early-warning flag to the CRM.
4. Re-forecast monthly and track MAPE to keep the quota defensible.
