# CloudPulse AI ⚡
> **Autonomous Cloud Telemetry & Predictive Analytics Engine**  
> Built with Python Flask, pandas, NumPy, Chart.js, HTML5 & CSS3.

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/Unit%20Tests-13%20Passed%20(100%25)-success.svg)](file:///c:/Users/kidhiyonprabu/OneDrive/Apps/CloudPulse_AI/tests/test_app.py)
[![UI Theme](https://img.shields.io/badge/Theme-Dark%20Navy%20%26%20Electric%20Cyan-06B6D4.svg)](#)

---

## 🌟 Executive Overview

**CloudPulse AI** is an enterprise-grade cloud resource monitoring, anomaly detection, and predictive capacity planning dashboard. Designed with an ultra-modern dark navy (`#0B1120`, `#0F172A`) and electric cyan (`#06B6D4`, `#22D3EE`) glassmorphic UI, it equips DevOps engineers, SREs, and cloud architects with real-time operational visibility and forward-looking time-series forecasts.

All buttons, charts, modals, and file upload/export flows are **100% functional and locally tested**.

---

## 🚀 Key Features

| Feature | Description |
| :--- | :--- |
| **Telemetry Metric Cards** | Real-time tracking of CPU Utilization (%), Memory Allocation (%), NVMe Storage Headroom (%), and Network Throughput (Mbps) with peak, mean, and minimum indicators. |
| **Interactive Charting** | Powered by [Chart.js](https://www.chartjs.org/) with multi-metric streams, dual Y-axes, smooth Bézier curves, and customizable filters. |
| **Moving Average Forecasting** | Recursive step-ahead predictions across **3, 5, and 7-observation windows** to evaluate the trade-off between rapid responsiveness and noise dampening. |
| **CO3: Uncertainty & Spike Detection** | Transparent dynamic confidence corridors $(\mu_t \pm 2\sigma_t)$ quantifying network burst stochasticity and flagging anomalous traffic surges. |
| **CO5: Chronological Validation** | Strict chronological train/test partitioning (anti-lookahead) computing Mean Absolute Error (**MAE**) and Root Mean Squared Error (**RMSE**). |
| **AI Resource Scaling Rules** | Proactive heuristics evaluating compute saturation, memory leaks, storage depletion, and ingress bandwidth surges. |
| **Configurable Operational Alerts** | Interactive modal allowing runtime customization of CPU, RAM, Disk, Network, and $Z$-score thresholds. |
| **CSV Upload & Live Preview** | Drag-and-drop CSV uploader with automatic header mapping and immediate 10-row dataset explorer. |
| **Report Export & Sample Download** | Instant one-click CSV report export bundling telemetry, MA predictions, uncertainty bands, and alert statuses. |
| **Demo Mode Safeguards** | Clear visual badges labeling synthetic sample data as **DEMO DATA**, with a one-click **Reset Demo** toggle. |

---

## 🧠 In-Depth Academic & Engineering Concepts

### 1. CO3: Uncertain Network Traffic Prediction & Dynamic Anomaly Bounds

```
                ▲ Network Ingress (Mbps)
                │                                         [Traffic Spike]
                │                                                ▲  (945 Mbps)
  Upper Bound ──┼─────────────────. . . . - - - - ──────────────/ \───────────
   (μ + 2σ)     │               .´               `.            /   \
  Baseline (μ)  │  ───────. - -´                   `- - .─────/─────\─────────
  Lower Bound ──┼────────´                                   /       \
   (μ - 2σ)     │                                           /         \
                │                                          /           \
                └─────────────────────────────────────────┴─────────────┴──────► Time
```

- **The Challenge of Network Stochasticity**: Unlike compute or disk usage that scale predictably with process counts, packet arrival in distributed cloud architectures is inherently non-stationary and bursty (Poisson arrivals, heavy-tailed file transfers, botnet DDoS attacks, and batch ETL jobs).
- **Why Deterministic Point Forecasts Fail**: A scalar prediction (e.g. *"Next 5-min throughput: 320 Mbps"*) hides variance. An auto-scaler relying on a single number will either under-provision (causing dropped TCP packets and SLA breaches) or over-provision (wasting budget).
- **The CloudPulse AI Solution**:
  1. Computes a moving baseline $\mu_t = \frac{1}{w}\sum_{i=1}^w y_{t-i}$.
  2. Dynamically estimates local standard deviation $\sigma_t$ with an empirical floor representing network jitter.
  3. Constructs the transparent confidence envelope:
     $$\text{Upper Bound}_t = \mu_t + k \cdot \sigma_t, \quad \text{Lower Bound}_t = \max(0, \mu_t - k \cdot \sigma_t)$$
  4. Points penetrating $\text{Upper Bound}_t$ with high statistical significance ($Z \ge 2.0$) trigger immediate ingress alarms and auto-scaling recommendations.

---

### 2. CO5: Chronological Model Validation & Time-Series Rigor

```
 Chronological Partitioning (Valid)
 ┌──────────────────────────────────────────────┬─────────────────────────┐
 │        Training Horizon (75%)                │   Evaluation Test (25%) │
 │        [t_0  ──────►  t_split]               │   [t_split+1 ────► t_n] │
 └──────────────────────────────────────────────┴─────────────────────────┘
  * Evaluates strictly forward in time. Zero future data leaks into the past.

 Random k-Fold Cross-Validation (INVALID for Time-Series!)
 ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
 │Trn│Tst│Trn│Trn│Tst│Trn│Tst│Trn│Trn│Tst│Trn│Trn│Tst│Trn│Trn│Tst│Trn│Trn│
 └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
  * CATASTROPHIC LOOKAHEAD BIAS: Training on tomorrow to predict yesterday.
```

- **Temporal Order Invariance**: In physical time-series, future events cannot causally influence past states. Shuffling telemetry records in standard cross-validation causes **Lookahead Data Leakage**, artificially deflating error rates and delivering false confidence.
- **Out-of-Sample Evaluation**: CloudPulse AI strictly splits historical data chronologically at $T_{split}$ (configurable at 70%, 75%, or 80%). The models generate step-ahead predictions across unseen test periods using only past observations.
- **Error Metric Mechanics**:
  - **Mean Absolute Error (MAE)**:
    $$\text{MAE} = \frac{1}{m} \sum_{i=1}^m |y_i - \hat{y}_i|$$
    *Measures the average error magnitude linearly in native units (Mbps, % CPU).*
  - **Root Mean Squared Error (RMSE)**:
    $$\text{RMSE} = \sqrt{\frac{1}{m} \sum_{i=1}^m (y_i - \hat{y}_i)^2}$$
    *Squares residuals before averaging, heavily penalizing large outliers. Critical for cloud systems where large errors cause catastrophic downtime.*

---

## 💻 Windows Setup Instructions (PowerShell)

### Prerequisites
- Windows 10 / 11
- Python 3.10 or higher installed (verify with `python --version`)

### Step 1: Open PowerShell in Workspace
Open Windows PowerShell and navigate to the project folder:
```powershell
cd c:\Users\kidhiyonprabu\OneDrive\Apps\CloudPulse_AI
```

### Step 2: Create a Python Virtual Environment
```powershell
python -m venv venv
```

### Step 3: Activate the Virtual Environment
```powershell
# If script execution is restricted, allow for current session:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Activate virtual environment:
.\venv\Scripts\Activate.ps1
```
*(Your command prompt should now display `(venv)`)*

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Execute Automated Test Suite
Verify that all 13 unit tests pass:
```powershell
python -m unittest tests/test_app.py
```
*Expected Output:*
```text
.............
----------------------------------------------------------------------
Ran 13 tests in 0.35s

OK
```

### Step 6: Launch the CloudPulse AI Web Server
```powershell
python app.py
```
*Expected Output:*
```text
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### Step 7: Access the Dashboard
Open your web browser (Chrome, Edge, Firefox) and navigate to:
```
http://127.0.0.1:5000
```

---

## 🌐 GitHub & Render Deployment Guide

### A. Pushing to GitHub
1. Initialize git and commit your files (the included `.gitignore` will automatically prevent virtual environments and cache files from being tracked):
   ```powershell
   git init
   git add .
   git commit -m "Initial commit: CloudPulse AI ready for production"
   ```
2. Create a repository on [GitHub](https://github.com/new).
3. Link and push to your remote repository:
   ```powershell
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git push -u origin main
   ```

### B. Deploying on Render (Free Web Service)
1. Sign in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the Web Service settings:
   - **Name**: `cloudpulse-ai` (or your preferred name)
   - **Region**: Choose the closest region (e.g., Oregon, Frankfurt, Singapore)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`
5. Click **Create Web Service**. Render will automatically run the build command, install dependencies including `gunicorn`, and start the app at your custom Render URL (`https://<your-service>.onrender.com`).

*(Note: `render.yaml` is also included in the repository for optional 1-click Blueprint deployment).*

---

## 📁 Project Directory Structure

```
CloudPulse_AI/
├── .gitignore                  # Git exclusion rules (venv, __pycache__, .env, secrets)
├── render.yaml                 # Render Blueprint configuration for deployment
├── app.py                      # Core Flask backend & predictive REST APIs (exposes 'app')
├── requirements.txt            # Python dependencies (Flask, pandas, numpy, gunicorn)
├── README.md                   # Comprehensive guide, Windows & Render documentation
├── data/
│   └── sample_cloud_metrics.csv # Synthetic telemetry dataset with labeled bursts (DEMO)
├── templates/
│   └── index.html              # Responsive single-page dashboard template
├── static/
│   ├── css/
│   │   └── style.css           # Dark navy & cyan glassmorphic stylesheet
│   └── js/
│       └── app.js              # Chart.js visualization, modals & reactive state
└── tests/
    └── test_app.py             # 13 automated unit tests (100% passing)
```

---

## 🔌 API Endpoint Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the main responsive dashboard interface |
| `GET` | `/api/status` | Returns system health, dataset origin (`DEMO`/`CUSTOM`), and active limits |
| `GET` | `/api/metrics` | Returns live telemetry points, summary metrics, and active alert violations |
| `GET` | `/api/predict` | Computes MA-3, MA-5, MA-7 predictions and step-ahead future forecasts |
| `GET` | `/api/spikes` | Returns CO3 uncertainty intervals, upper/lower bounds, and anomaly spikes |
| `GET` | `/api/validation` | Performs CO5 chronological train/test split and computes MAE & RMSE |
| `GET` | `/api/recommendations` | Generates rule-based AI resource scaling recommendations |
| `POST` | `/api/upload` | Uploads and parses custom CSV telemetry datasets |
| `POST` | `/api/alerts/config` | Modifies runtime alert thresholds for CPU, RAM, Disk, and Network |
| `POST` | `/api/reset-demo` | Restores standard demo cloud metrics dataset |
| `GET` | `/api/export-report` | Downloads CSV analytical report with telemetry and projections |
| `GET` | `/api/sample-download` | Serves reference `sample_cloud_metrics.csv` for user download |

---

## 📊 CSV Telemetry Schema

When uploading custom CSV files, CloudPulse AI accepts standard time-series formats with column auto-matching:

| Field Name | Type | Example | Description |
| :--- | :--- | :--- | :--- |
| `timestamp` | Datetime / String | `2026-10-10 08:00:00` | Chronological sample time |
| `cpu_usage` | Float (%) | `42.5` | Processor consumption percentage |
| `memory_usage` | Float (%) | `68.2` | Resident memory allocation percentage |
| `storage_usage` | Float (%) | `53.1` | Persistent volume consumption percentage |
| `network_in_mbps` | Float (Mbps) | `310.4` | Ingress network throughput |
| `network_out_mbps` | Float (Mbps) | `265.8` | Egress network throughput |
| `latency_ms` | Float (ms) | `22.4` | Round-trip request response time |

---

## 🛡️ License & Academic Integrity

Developed for academic demonstration and enterprise observability benchmarking. All synthetic datasets are clearly demarcated for educational and test demonstration purposes.
