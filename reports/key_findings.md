# VoltPulse AI — Key Findings Report

Generated from processed aggregates. All figures are computed from data.

## Headline metrics
- Swap attempts: **3,877,013** | completed: **3,645,809** | success rate: **94.0%**
- Revenue: **₹23.31 Cr** | rev/completed swap: **₹64**
- Failed swaps: **145,959** (6.0% of attempts)

## Monthly trend (first → last)
- 2024-01: 105,490 completed, 95.6% success
- 2025-06: 307,259 completed, 91.4% success

## City comparison
- **Bengaluru**: 825,327 attempts, 95.4% success, ₹519.5L revenue, 23,090 failures
- **Delhi NCR**: 768,913 attempts, 92.6% success, ₹445.7L revenue, 36,197 failures
- **Hyderabad**: 711,930 attempts, 93.3% success, ₹415.2L revenue, 30,427 failures
- **Pune**: 552,910 attempts, 95.0% success, ₹347.7L revenue, 17,127 failures
- **Mumbai**: 530,299 attempts, 95.6% success, ₹320.9L revenue, 14,441 failures
- **Jaipur**: 487,634 attempts, 92.2% success, ₹282.3L revenue, 24,677 failures

## Failure hotspots (top 5 stations by risk score)
- STN-DEL-048 (Delhi NCR): fail 5.7%, abandon 2.8%, queue 4.1 min, risk 0.899, conn=good, Gen1
- STN-DEL-037 (Delhi NCR): fail 5.9%, abandon 2.8%, queue 4.0 min, risk 0.884, conn=good, Gen1
- STN-JAI-142 (Jaipur): fail 5.5%, abandon 2.8%, queue 4.1 min, risk 0.884, conn=poor, Gen1
- STN-JAI-141 (Jaipur): fail 5.7%, abandon 2.7%, queue 4.1 min, risk 0.861, conn=good, Gen1
- STN-DEL-045 (Delhi NCR): fail 5.7%, abandon 2.6%, queue 4.1 min, risk 0.835, conn=good, Gen1

## Rider churn
- active: 9,440 riders (avg 248.3 swaps, fail rate 4.1%)
- at_risk: 754 riders (avg 238.6 swaps, fail rate 4.6%)
- churned: 7,842 riders (avg 138.0 swaps, fail rate 4.1%)
- new: 1,914 riders (avg 20.9 swaps, fail rate 5.8%)

## Battery health
- 6,500 batteries; mean SOH 88.1%; 4,556 below 90% SOH

## Recommendations (Decision Center)
- **[High] 39% of riders are churned** — At-risk pool: 754 riders.
- **[Medium] Discount rate rising — margin erosion** — Revenue impact ≈ 5,230,378 INR forgone vs early-period rate.
- **[Medium] Degraded batteries correlate with swap failures** — Failure reduction directly lifts success rate and rider retention.
- **[Low] Support tickets dominated by 'no_battery_available' (26%)** — Lower ticket volume → lower support cost, higher CSAT.