"""
CloudPulse AI - Intelligent Cloud Telemetry & Predictive Analytics Engine
Framework: Flask, pandas, NumPy
"""

import io
import os
import csv
from datetime import datetime
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file, Response

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.secret_key = os.environ.get('SECRET_KEY', 'cloudpulse-ai-secret-key-2026')

# Path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SAMPLE_CSV_PATH = os.path.join(DATA_DIR, 'sample_cloud_metrics.csv')

# Global runtime state
CURRENT_STATE: Dict[str, Any] = {
    'df': None,
    'is_demo': True,
    'filename': 'sample_cloud_metrics.csv',
    'last_updated': None,
    'alert_thresholds': {
        'cpu_threshold': 80.0,
        'memory_threshold': 80.0,
        'storage_threshold': 75.0,
        'network_threshold': 600.0,
        'spike_zscore': 2.0
    }
}


def load_default_data() -> pd.DataFrame:
    """Load or generate baseline demo dataset."""
    if os.path.exists(SAMPLE_CSV_PATH):
        df = pd.read_csv(SAMPLE_CSV_PATH)
    else:
        # Fallback synthetic generation if file missing
        timestamps = pd.date_range(start="2026-10-10 08:00:00", periods=60, freq="5min")
        np.random.seed(42)
        cpu = 30 + 35 * np.sin(np.linspace(0, 3 * np.pi, 60)) + np.random.normal(0, 3, 60)
        cpu = np.clip(cpu, 10, 98)
        mem = 45 + 25 * np.sin(np.linspace(0, 2.5 * np.pi, 60)) + np.random.normal(0, 2, 60)
        mem = np.clip(mem, 25, 95)
        storage = 52.0 + np.linspace(0, 3, 60)
        net_in = 150 + 200 * (cpu / 100) ** 1.5 + np.random.normal(0, 15, 60)
        # Inject realistic burst spikes
        net_in[24:27] += 550
        net_in[48:51] += 480
        net_out = net_in * 0.85 + np.random.normal(0, 10, 60)
        latency = 18 + (cpu / 100) * 40 + (net_in / 1000) * 35

        df = pd.DataFrame({
            'timestamp': [t.strftime("%Y-%m-%d %H:%M:%S") for t in timestamps],
            'cpu_usage': np.round(cpu, 1),
            'memory_usage': np.round(mem, 1),
            'storage_usage': np.round(storage, 1),
            'network_in_mbps': np.round(net_in, 1),
            'network_out_mbps': np.round(net_out, 1),
            'latency_ms': np.round(latency, 1)
        })
        os.makedirs(DATA_DIR, exist_ok=True)
        df.to_csv(SAMPLE_CSV_PATH, index=False)

    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def initialize_runtime():
    """Initializes in-memory telemetry state."""
    CURRENT_STATE['df'] = load_default_data()
    CURRENT_STATE['is_demo'] = True
    CURRENT_STATE['filename'] = 'sample_cloud_metrics.csv'
    CURRENT_STATE['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


initialize_runtime()


def calculate_moving_average_forecast(series: pd.Series, window: int) -> pd.Series:
    """
    Computes step-ahead moving average forecast for time-series.
    Forecast for index t uses observations [t-window ... t-1], shifting by 1
    to eliminate lookahead bias.
    """
    return series.shift(1).rolling(window=window, min_periods=window).mean()


def compute_uncertainty_and_spikes(df: pd.DataFrame, metric: str = 'network_in_mbps',
                                   window: int = 5, k_std: float = 2.0) -> Dict[str, Any]:
    """
    CO3 - Uncertain Network Traffic Prediction & Spike Detection.
    Computes rolling mean baseline, rolling standard deviation (uncertainty width),
    upper/lower uncertainty bands, and flags anomalous traffic bursts.
    """
    values = df[metric].astype(float)
    # Rolling baseline and rolling standard deviation
    rolling_mean = values.shift(1).rolling(window=window, min_periods=max(2, window // 2)).mean()
    rolling_mean = rolling_mean.fillna(values.expanding().mean())

    raw_std = values.shift(1).rolling(window=window, min_periods=max(2, window // 2)).std()
    raw_std = raw_std.fillna(values.std() if not pd.isna(values.std()) else 15.0)
    # Floor standard deviation to at least 15% of rolling mean or 20 Mbps to model real-world network jitter
    rolling_std = np.maximum(raw_std, np.maximum(0.15 * rolling_mean, 20.0))

    upper_bound = rolling_mean + (k_std * rolling_std)
    lower_bound = np.maximum(0.0, rolling_mean - (k_std * rolling_std))

    # Spike detection: Exceeds dynamic upper uncertainty bound OR global extreme anomaly
    global_mean = values.mean()
    global_std = max(values.std(), 1.0)
    global_z = (values - global_mean) / global_std
    local_z = (values - rolling_mean) / rolling_std

    spike_thresh_z = CURRENT_STATE['alert_thresholds']['spike_zscore']
    is_spike = (values > upper_bound) & (global_z >= 1.5)

    spikes_list = []
    for idx, spike in enumerate(is_spike):
        if spike:
            val = float(values.iloc[idx])
            ub = float(upper_bound.iloc[idx])
            gz = float(global_z.iloc[idx])
            lz = float(local_z.iloc[idx])
            effective_z = max(gz, lz)
            spikes_list.append({
                'index': idx,
                'timestamp': str(df['timestamp'].iloc[idx]),
                'value': round(val, 2),
                'upper_bound': round(ub, 2),
                'excess_mbps': round(max(0.0, val - ub), 2),
                'z_score': round(effective_z, 2),
                'severity': 'Critical' if effective_z >= 2.5 else 'High'
            })

    # Summary metrics
    avg_band_width = float((upper_bound - lower_bound).mean())
    max_uncertainty = float((upper_bound - lower_bound).max())

    return {
        'metric': metric,
        'window': window,
        'confidence_multiplier': k_std,
        'timestamps': df['timestamp'].tolist(),
        'actual': np.round(values, 2).tolist(),
        'baseline_prediction': np.round(rolling_mean, 2).tolist(),
        'upper_bound': np.round(upper_bound, 2).tolist(),
        'lower_bound': np.round(lower_bound, 2).tolist(),
        'is_spike': is_spike.astype(bool).tolist(),
        'detected_spikes': spikes_list,
        'total_spikes': len(spikes_list),
        'spike_percentage': round((len(spikes_list) / len(df)) * 100, 1),
        'uncertainty_stats': {
            'average_bandwidth_uncertainty': round(avg_band_width, 2),
            'peak_uncertainty_interval': round(max_uncertainty, 2),
            'global_std_dev': round(global_std, 2)
        }
    }


def perform_chronological_validation(df: pd.DataFrame, metric: str = 'network_in_mbps',
                                      train_ratio: float = 0.75) -> Dict[str, Any]:
    """
    CO5 - Model Validation in Time-Series.
    Strict chronological temporal split into train and test sets to prevent
    lookahead data leakage. Computes MAE and RMSE across 3, 5, and 7 Moving Averages.
    """
    values = df[metric].astype(float).values
    n = len(values)
    split_idx = int(n * train_ratio)

    train_data = values[:split_idx]
    test_data = values[split_idx:]
    test_timestamps = df['timestamp'].iloc[split_idx:].tolist()

    windows = [3, 5, 7]
    validation_results = {}
    best_window = 3
    lowest_mae = float('inf')

    # Step-ahead evaluation over the test horizon
    for w in windows:
        predictions = []
        actuals = []

        # Predict each test index t using its prior w observations
        for t in range(split_idx, n):
            prior_window = values[t - w: t]
            pred = float(np.mean(prior_window))
            predictions.append(pred)
            actuals.append(float(values[t]))

        errors = np.array(actuals) - np.array(predictions)
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))

        if mae < lowest_mae:
            lowest_mae = mae
            best_window = w

        validation_results[f"MA_{w}"] = {
            'window': w,
            'mae': round(mae, 3),
            'rmse': round(rmse, 3),
            'predictions': np.round(predictions, 2).tolist(),
            'actuals': np.round(actuals, 2).tolist()
        }

    return {
        'metric': metric,
        'train_ratio': train_ratio,
        'total_samples': n,
        'train_samples': split_idx,
        'test_samples': n - split_idx,
        'split_timestamp': df['timestamp'].iloc[split_idx],
        'test_timestamps': test_timestamps,
        'models': validation_results,
        'best_model': f"MA_{best_window}",
        'explanation': (
            "Chronological validation preserves temporal ordering (t_0 < t_1 < ... < t_n). "
            "Standard k-fold cross-validation is invalid for cloud time-series because shuffling "
            "leaks future telemetry states into past training samples."
        )
    }


def generate_scaling_recommendations(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    AI Heuristic Resource Scaling Recommendations.
    Analyzes telemetry capacity limits, compute starvation, and network bottlenecks.
    """
    recommendations = []
    
    cpu_p95 = float(np.percentile(df['cpu_usage'], 95))
    cpu_mean = float(df['cpu_usage'].mean())
    mem_p95 = float(np.percentile(df['memory_usage'], 95))
    storage_max = float(df['storage_usage'].max())
    net_p95 = float(np.percentile(df['network_in_mbps'], 95))

    # CPU Assessment
    if cpu_p95 > 85.0 or cpu_mean > 70.0:
        recommendations.append({
            'type': 'Compute Scale-Out',
            'severity': 'Critical',
            'badge': 'Scale Up / Out',
            'current_metric': f"CPU 95th Percentile: {round(cpu_p95, 1)}%",
            'action': 'Trigger Horizontal Pod Autoscaler (HPA) to spawn +2 worker nodes.',
            'rationale': 'Sustained compute load exceeds 85% headroom, posing latency breach risk under SLA.',
            'impact': 'Prevents throttling and drops response latency by ~40%.'
        })
    elif cpu_p95 < 25.0:
        recommendations.append({
            'type': 'Cost Optimization',
            'severity': 'Optimal',
            'badge': 'Scale In',
            'current_metric': f"CPU 95th Percentile: {round(cpu_p95, 1)}%",
            'action': 'Downscale idle nodes in auto-scaling group from 4 to 2 instances.',
            'rationale': 'Cluster is substantially over-provisioned during low-demand window.',
            'impact': 'Estimated monthly cloud cost reduction of ~35%.'
        })
    else:
        recommendations.append({
            'type': 'Compute Capacity',
            'severity': 'Normal',
            'badge': 'Balanced',
            'current_metric': f"CPU Mean: {round(cpu_mean, 1)}% (95th: {round(cpu_p95, 1)}%)",
            'action': 'Maintain existing node count and current CPU burst credits.',
            'rationale': 'Processor utilization is optimal with healthy safety margin.',
            'impact': 'SLA margins maintained within target parameters.'
        })

    # Memory Assessment
    if mem_p95 > 80.0:
        recommendations.append({
            'type': 'Memory Provisioning',
            'severity': 'High',
            'badge': 'Upgrade RAM',
            'current_metric': f"RAM 95th Percentile: {round(mem_p95, 1)}%",
            'action': 'Upgrade container memory limit or migrate to memory-optimized instances (e.g. r6i.xlarge).',
            'rationale': 'High memory footprint increases OOM-killer (Out-Of-Memory) eviction risk.',
            'impact': 'Eliminates unexpected microservice pod crashes and GC pauses.'
        })

    # Storage Headroom
    if storage_max > 75.0:
        recommendations.append({
            'type': 'Storage Expansion',
            'severity': 'Medium',
            'badge': 'Expand Volume',
            'current_metric': f"Disk Usage: {round(storage_max, 1)}%",
            'action': 'Trigger dynamic volume expansion (+100 GB NVMe SSD).',
            'rationale': 'Persistent volume capacity is approaching warning threshold (75%).',
            'impact': 'Prevents read-only volume lockups during database logging.'
        })

    # Network Throughput Assessment
    if net_p95 > 600.0:
        recommendations.append({
            'type': 'Traffic & CDN Offloading',
            'severity': 'Critical',
            'badge': 'Edge Caching',
            'current_metric': f"Peak Network Throughput: {round(net_p95, 1)} Mbps",
            'action': 'Activate CloudFront/Cloudflare edge CDN caching and enable rate-limiting rules.',
            'rationale': 'Repeated ingress surges cause network interface saturation and egress cost escalation.',
            'impact': 'Offloads up to 65% of raw network requests from ingress gateways.'
        })

    return recommendations


# ==========================================
# Flask Routes
# ==========================================

@app.route('/')
def index():
    """Renders the CloudPulse AI interactive dashboard."""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def api_status():
    """Returns runtime health and active dataset metadata."""
    df = CURRENT_STATE['df']
    return jsonify({
        'status': 'healthy',
        'is_demo': CURRENT_STATE['is_demo'],
        'filename': CURRENT_STATE['filename'],
        'records_count': len(df) if df is not None else 0,
        'last_updated': CURRENT_STATE['last_updated'],
        'thresholds': CURRENT_STATE['alert_thresholds']
    })


@app.route('/api/metrics', methods=['GET'])
def api_metrics():
    """Returns primary telemetry points, summary statistics, and active alerts."""
    df = CURRENT_STATE['df']
    if df is None:
        initialize_runtime()
        df = CURRENT_STATE['df']

    latest_row = df.iloc[-1].to_dict()

    # Calculate overall metrics
    summary = {
        'cpu': {
            'current': float(latest_row['cpu_usage']),
            'mean': round(float(df['cpu_usage'].mean()), 1),
            'max': round(float(df['cpu_usage'].max()), 1),
            'min': round(float(df['cpu_usage'].min()), 1)
        },
        'memory': {
            'current': float(latest_row['memory_usage']),
            'mean': round(float(df['memory_usage'].mean()), 1),
            'max': round(float(df['memory_usage'].max()), 1),
            'min': round(float(df['memory_usage'].min()), 1)
        },
        'storage': {
            'current': float(latest_row['storage_usage']),
            'mean': round(float(df['storage_usage'].mean()), 1),
            'max': round(float(df['storage_usage'].max()), 1),
            'min': round(float(df['storage_usage'].min()), 1)
        },
        'network_in': {
            'current': float(latest_row['network_in_mbps']),
            'mean': round(float(df['network_in_mbps'].mean()), 1),
            'max': round(float(df['network_in_mbps'].max()), 1),
            'min': round(float(df['network_in_mbps'].min()), 1)
        },
        'network_out': {
            'current': float(latest_row['network_out_mbps']),
            'mean': round(float(df['network_out_mbps'].mean()), 1),
            'max': round(float(df['network_out_mbps'].max()), 1)
        },
        'latency': {
            'current': float(latest_row.get('latency_ms', 20.0)),
            'mean': round(float(df.get('latency_ms', pd.Series([20.0])).mean()), 1)
        }
    }

    # Evaluate dynamic alerts against thresholds
    thresh = CURRENT_STATE['alert_thresholds']
    active_alerts = []
    
    high_cpu_count = int((df['cpu_usage'] > thresh['cpu_threshold']).sum())
    if high_cpu_count > 0:
        active_alerts.append({
            'metric': 'CPU Utilization',
            'severity': 'Critical',
            'message': f"CPU exceeded {thresh['cpu_threshold']}% in {high_cpu_count} observations (Peak: {summary['cpu']['max']}%)."
        })

    high_mem_count = int((df['memory_usage'] > thresh['memory_threshold']).sum())
    if high_mem_count > 0:
        active_alerts.append({
            'metric': 'Memory Consumption',
            'severity': 'Warning',
            'message': f"RAM crossed {thresh['memory_threshold']}% threshold in {high_mem_count} observations."
        })

    high_net_count = int((df['network_in_mbps'] > thresh['network_threshold']).sum())
    if high_net_count > 0:
        active_alerts.append({
            'metric': 'Network Ingress Surge',
            'severity': 'Critical',
            'message': f"Network traffic surpassed {thresh['network_threshold']} Mbps in {high_net_count} telemetry samples."
        })

    return jsonify({
        'is_demo': CURRENT_STATE['is_demo'],
        'filename': CURRENT_STATE['filename'],
        'records_count': len(df),
        'summary': summary,
        'active_alerts': active_alerts,
        'series': {
            'timestamps': df['timestamp'].tolist(),
            'cpu': df['cpu_usage'].tolist(),
            'memory': df['memory_usage'].tolist(),
            'storage': df['storage_usage'].tolist(),
            'network_in': df['network_in_mbps'].tolist(),
            'network_out': df['network_out_mbps'].tolist(),
            'latency': df['latency_ms'].tolist() if 'latency_ms' in df.columns else []
        }
    })


@app.route('/api/predict', methods=['GET'])
def api_predict():
    """
    Computes Moving Average predictions (3, 5, 7 observations) for selected metric.
    Includes actual vs predicted curves and next-step future forecast.
    """
    df = CURRENT_STATE['df']
    if df is None:
        initialize_runtime()
        df = CURRENT_STATE['df']

    metric = request.args.get('metric', 'cpu_usage')
    if metric not in df.columns:
        metric = 'cpu_usage'

    series = df[metric].astype(float)
    timestamps = df['timestamp'].tolist()

    # Moving Average predictions for windows 3, 5, 7
    ma_3 = calculate_moving_average_forecast(series, window=3)
    ma_5 = calculate_moving_average_forecast(series, window=5)
    ma_7 = calculate_moving_average_forecast(series, window=7)

    # Calculate next observation prediction (step n+1)
    next_3 = float(np.mean(series.iloc[-3:].values))
    next_5 = float(np.mean(series.iloc[-5:].values))
    next_7 = float(np.mean(series.iloc[-7:].values))

    # Error residuals for each window
    err_3 = float(np.nanmean(np.abs(series - ma_3)))
    err_5 = float(np.nanmean(np.abs(series - ma_5)))
    err_7 = float(np.nanmean(np.abs(series - ma_7)))

    def clean_nans(s: pd.Series) -> List[Any]:
        return [round(x, 2) if not np.isnan(x) else None for x in s]

    return jsonify({
        'metric': metric,
        'timestamps': timestamps,
        'actual': np.round(series, 2).tolist(),
        'ma_3': clean_nans(ma_3),
        'ma_5': clean_nans(ma_5),
        'ma_7': clean_nans(ma_7),
        'mae_summary': {
            'ma_3': round(err_3, 3),
            'ma_5': round(err_5, 3),
            'ma_7': round(err_7, 3)
        },
        'next_prediction': {
            'ma_3': round(next_3, 2),
            'ma_5': round(next_5, 2),
            'ma_7': round(next_7, 2)
        }
    })


@app.route('/api/spikes', methods=['GET'])
def api_spikes():
    """
    CO3 Endpoint: Network Traffic Spike Detection & Transparent Uncertainty Bounds.
    """
    df = CURRENT_STATE['df']
    if df is None:
        initialize_runtime()
        df = CURRENT_STATE['df']

    metric = request.args.get('metric', 'network_in_mbps')
    if metric not in df.columns:
        metric = 'network_in_mbps'

    try:
        window = int(request.args.get('window', 5))
        k_std = float(request.args.get('k_std', 2.0))
    except ValueError:
        window = 5
        k_std = 2.0

    result = compute_uncertainty_and_spikes(df, metric=metric, window=window, k_std=k_std)
    return jsonify(result)


@app.route('/api/validation', methods=['GET'])
def api_validation():
    """
    CO5 Endpoint: Chronological Train/Test Validation with MAE and RMSE Metrics.
    """
    df = CURRENT_STATE['df']
    if df is None:
        initialize_runtime()
        df = CURRENT_STATE['df']

    metric = request.args.get('metric', 'network_in_mbps')
    if metric not in df.columns:
        metric = 'network_in_mbps'

    try:
        train_ratio = float(request.args.get('train_ratio', 0.75))
    except ValueError:
        train_ratio = 0.75

    result = perform_chronological_validation(df, metric=metric, train_ratio=train_ratio)
    return jsonify(result)


@app.route('/api/recommendations', methods=['GET'])
def api_recommendations():
    """Generates AI Resource Scaling Recommendations based on active data."""
    df = CURRENT_STATE['df']
    if df is None:
        initialize_runtime()
        df = CURRENT_STATE['df']

    recs = generate_scaling_recommendations(df)
    return jsonify({
        'is_demo': CURRENT_STATE['is_demo'],
        'recommendations': recs,
        'count': len(recs)
    })


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    Accepts CSV upload, validates required telemetry fields,
    updates runtime state, and returns tabular preview.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for upload'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400

    try:
        content = file.read().decode('utf-8', errors='ignore')
        df = pd.read_csv(io.StringIO(content))

        if len(df) < 5:
            return jsonify({'error': 'Dataset too small. Must contain at least 5 telemetry records.'}), 400

        # Normalization and column mapping
        col_map = {}
        for c in df.columns:
            low = c.strip().lower()
            if 'time' in low or 'date' in low:
                col_map[c] = 'timestamp'
            elif 'cpu' in low:
                col_map[c] = 'cpu_usage'
            elif 'mem' in low or 'ram' in low:
                col_map[c] = 'memory_usage'
            elif 'disk' in low or 'stor' in low:
                col_map[c] = 'storage_usage'
            elif 'net_in' in low or 'network_in' in low or 'ingress' in low:
                col_map[c] = 'network_in_mbps'
            elif 'net_out' in low or 'network_out' in low or 'egress' in low:
                col_map[c] = 'network_out_mbps'
            elif 'latency' in low or 'ping' in low:
                col_map[c] = 'latency_ms'

        df = df.rename(columns=col_map)

        # Fallbacks for missing non-essential columns
        if 'timestamp' not in df.columns:
            df['timestamp'] = pd.date_range(end=datetime.now(), periods=len(df), freq='5min').strftime("%Y-%m-%d %H:%M:%S")
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce').fillna(pd.Timestamp.now()).dt.strftime("%Y-%m-%d %H:%M:%S")

        if 'cpu_usage' not in df.columns:
            return jsonify({'error': 'Missing required CPU telemetry column (e.g., cpu_usage, cpu_percent).'}), 400

        if 'memory_usage' not in df.columns:
            df['memory_usage'] = 50.0

        if 'storage_usage' not in df.columns:
            df['storage_usage'] = 50.0

        if 'network_in_mbps' not in df.columns:
            df['network_in_mbps'] = df['cpu_usage'] * 4.0

        if 'network_out_mbps' not in df.columns:
            df['network_out_mbps'] = df['network_in_mbps'] * 0.8

        if 'latency_ms' not in df.columns:
            df['latency_ms'] = 25.0

        # Cast to numeric
        for col in ['cpu_usage', 'memory_usage', 'storage_usage', 'network_in_mbps', 'network_out_mbps', 'latency_ms']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        CURRENT_STATE['df'] = df
        CURRENT_STATE['is_demo'] = False
        CURRENT_STATE['filename'] = file.filename
        CURRENT_STATE['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Preview of first 10 rows
        preview_rows = df.head(10).to_dict(orient='records')

        return jsonify({
            'success': True,
            'message': f"Successfully loaded {len(df)} records from {file.filename}.",
            'filename': file.filename,
            'records_count': len(df),
            'columns': df.columns.tolist(),
            'preview': preview_rows
        })

    except Exception as e:
        return jsonify({'error': f"Failed to process CSV file: {str(e)}"}), 500


@app.route('/api/reset-demo', methods=['POST'])
def api_reset_demo():
    """Resets application back to standard demo dataset."""
    initialize_runtime()
    return jsonify({
        'success': True,
        'message': 'Successfully restored CloudPulse AI demo dataset.',
        'is_demo': True,
        'filename': 'sample_cloud_metrics.csv',
        'records_count': len(CURRENT_STATE['df'])
    })


@app.route('/api/alerts/config', methods=['POST'])
def api_alerts_config():
    """Updates configurable alert threshold parameters."""
    data = request.get_json() or {}
    for key in CURRENT_STATE['alert_thresholds']:
        if key in data:
            try:
                CURRENT_STATE['alert_thresholds'][key] = float(data[key])
            except ValueError:
                pass

    return jsonify({
        'success': True,
        'message': 'Alert thresholds updated successfully.',
        'thresholds': CURRENT_STATE['alert_thresholds']
    })


@app.route('/api/export-report', methods=['GET'])
def api_export_report():
    """
    Exports a comprehensive CSV report containing telemetry,
    Moving Average predictions (3, 5, 7), uncertainty bounds, and spike flags.
    """
    df = CURRENT_STATE['df']
    if df is None:
        initialize_runtime()
        df = CURRENT_STATE['df']

    # Generate analytical projections
    report_df = df.copy()
    
    # Predictions for CPU and Network
    report_df['cpu_ma3'] = calculate_moving_average_forecast(report_df['cpu_usage'], 3).round(2)
    report_df['cpu_ma5'] = calculate_moving_average_forecast(report_df['cpu_usage'], 5).round(2)
    report_df['cpu_ma7'] = calculate_moving_average_forecast(report_df['cpu_usage'], 7).round(2)

    net_uncertainty = compute_uncertainty_and_spikes(report_df, metric='network_in_mbps', window=5)
    report_df['net_upper_bound_mbps'] = net_uncertainty['upper_bound']
    report_df['net_lower_bound_mbps'] = net_uncertainty['lower_bound']
    report_df['net_spike_flag'] = net_uncertainty['is_spike']

    # Check alert violations
    thresh = CURRENT_STATE['alert_thresholds']
    report_df['cpu_alert'] = report_df['cpu_usage'] > thresh['cpu_threshold']
    report_df['mem_alert'] = report_df['memory_usage'] > thresh['memory_threshold']

    output = io.StringIO()
    report_df.to_csv(output, index=False)
    csv_bytes = output.getvalue().encode('utf-8')

    filename = f"CloudPulse_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@app.route('/api/sample-download', methods=['GET'])
def api_sample_download():
    """Serves the standard demo CSV dataset for user download."""
    if os.path.exists(SAMPLE_CSV_PATH):
        return send_file(SAMPLE_CSV_PATH, as_attachment=True, download_name="sample_cloud_metrics.csv", mimetype="text/csv")
    
    df = load_default_data()
    output = io.StringIO()
    df.to_csv(output, index=False)
    return Response(
        output.getvalue().encode('utf-8'),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=sample_cloud_metrics.csv"}
    )


if __name__ == '__main__':
    # Support dynamic PORT environment variable (e.g. Render/Cloud) or fallback to 5000
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(host='0.0.0.0', port=port, debug=debug)
