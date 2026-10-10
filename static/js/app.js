/**
 * CloudPulse AI - Dashboard Application Logic
 * Chart.js Visualizations, Telemetry Streams, Moving Average Forecasts,
 * CO3 Uncertainty/Spikes, CO5 Chronological Validation & Dynamic Controls
 */

document.addEventListener('DOMContentLoaded', () => {
    // State management
    const state = {
        activeFilter: 'all',
        forecastMetric: 'cpu_usage',
        forecastWindow: '3',
        spikeZScore: '2.0',
        trainRatio: '0.75',
        charts: {},
        selectedUploadFile: null
    };

    // Initialize application
    initDashboard();

    // -------------------------------------------------------------
    // Initialization & Event Binding
    // -------------------------------------------------------------
    function initDashboard() {
        setupChartDefaults();
        initEventListeners();
        fetchAllDashboardData();
    }

    function setupChartDefaults() {
        if (window.Chart) {
            Chart.defaults.color = '#94A3B8';
            Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
            Chart.defaults.plugins.tooltip.backgroundColor = '#0F172A';
            Chart.defaults.plugins.tooltip.titleColor = '#F8FAFC';
            Chart.defaults.plugins.tooltip.borderColor = '#334155';
            Chart.defaults.plugins.tooltip.borderWidth = 1;
            Chart.defaults.plugins.tooltip.padding = 10;
        }
    }

    function initEventListeners() {
        // Stream filter buttons (Chart 1)
        document.querySelectorAll('[data-metric-filter]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('[data-metric-filter]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.activeFilter = btn.dataset.metricFilter;
                fetchTelemetryData();
            });
        });

        // Forecast Metric selector (Chart 2)
        const metricSelect = document.getElementById('select-forecast-metric');
        if (metricSelect) {
            metricSelect.addEventListener('change', (e) => {
                state.forecastMetric = e.target.value;
                fetchForecastData();
            });
        }

        // Forecast Window buttons (Chart 2)
        document.querySelectorAll('[data-window]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('[data-window]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.forecastWindow = btn.dataset.window;
                fetchForecastData();
            });
        });

        // CO3 Spike sensitivity selector
        const spikeZSelect = document.getElementById('select-spike-zscore');
        if (spikeZSelect) {
            spikeZSelect.addEventListener('change', (e) => {
                state.spikeZScore = e.target.value;
                fetchSpikesData();
            });
        }

        // CO5 Train/Test split ratio selector
        const trainRatioSelect = document.getElementById('select-train-ratio');
        if (trainRatioSelect) {
            trainRatioSelect.addEventListener('change', (e) => {
                state.trainRatio = e.target.value;
                fetchValidationData();
            });
        }

        // Modals Controls
        setupModalControls();

        // Action Buttons
        setupActionButtons();
    }

    function setupModalControls() {
        // Upload Modal
        const modalUpload = document.getElementById('modal-upload');
        const openUploadBtns = [document.getElementById('btn-open-upload'), document.getElementById('btn-trigger-upload-modal')];
        const closeUploadBtns = [document.getElementById('btn-close-upload'), document.getElementById('btn-cancel-upload')];

        openUploadBtns.forEach(btn => {
            if (btn) btn.addEventListener('click', () => modalUpload.classList.add('active'));
        });
        closeUploadBtns.forEach(btn => {
            if (btn) btn.addEventListener('click', () => modalUpload.classList.remove('active'));
        });

        // Alerts Modal
        const modalAlerts = document.getElementById('modal-alerts');
        const openAlertsBtns = [document.getElementById('btn-open-alerts'), document.getElementById('btn-quick-config')];
        const closeAlertsBtns = [document.getElementById('btn-close-alerts'), document.getElementById('btn-cancel-alerts')];

        openAlertsBtns.forEach(btn => {
            if (btn) btn.addEventListener('click', () => {
                loadCurrentThresholdsIntoModal();
                modalAlerts.classList.add('active');
            });
        });
        closeAlertsBtns.forEach(btn => {
            if (btn) btn.addEventListener('click', () => modalAlerts.classList.remove('active'));
        });

        // Guide Modal
        const modalGuide = document.getElementById('modal-guide');
        const openGuideBtn = document.getElementById('btn-guide');
        const closeGuideBtns = [document.getElementById('btn-close-guide'), document.getElementById('btn-dismiss-guide')];

        if (openGuideBtn) {
            openGuideBtn.addEventListener('click', () => modalGuide.classList.add('active'));
        }
        closeGuideBtns.forEach(btn => {
            if (btn) btn.addEventListener('click', () => modalGuide.classList.remove('active'));
        });

        // Close on clicking outside modal card
        [modalUpload, modalAlerts, modalGuide].forEach(overlay => {
            if (overlay) {
                overlay.addEventListener('click', (e) => {
                    if (e.target === overlay) overlay.classList.remove('active');
                });
            }
        });
    }

    function setupActionButtons() {
        // Banner Dismiss
        const dismissBanner = document.getElementById('btn-dismiss-banner');
        if (dismissBanner) {
            dismissBanner.addEventListener('click', () => {
                const banner = document.getElementById('demo-banner');
                if (banner) banner.style.display = 'none';
            });
        }

        // Export CSV Report
        const exportBtn = document.getElementById('btn-export-csv');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                window.location.href = '/api/export-report';
                showToast('Generating analytical telemetry report...', 'success');
            });
        }

        // Download Sample CSV
        const sampleDlBtns = [document.getElementById('btn-download-sample-csv'), document.getElementById('btn-modal-sample-dl')];
        sampleDlBtns.forEach(btn => {
            if (btn) {
                btn.addEventListener('click', () => {
                    window.location.href = '/api/sample-download';
                    showToast('Downloading sample cloud metrics dataset.', 'success');
                });
            }
        });

        // Reset Demo Dataset
        const resetBtn = document.getElementById('btn-reset-demo');
        if (resetBtn) {
            resetBtn.addEventListener('click', async () => {
                try {
                    const res = await fetch('/api/reset-demo', { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        showToast(data.message, 'success');
                        fetchAllDashboardData();
                    }
                } catch (err) {
                    showToast('Failed to reset demo dataset.', 'error');
                }
            });
        }

        // Reload Table Preview
        const refreshTableBtn = document.getElementById('btn-refresh-preview');
        if (refreshTableBtn) {
            refreshTableBtn.addEventListener('click', () => {
                fetchTelemetryData();
                showToast('Telemetry preview table refreshed.', 'success');
            });
        }

        // Save Alert Thresholds
        const saveAlertsBtn = document.getElementById('btn-save-alerts');
        if (saveAlertsBtn) {
            saveAlertsBtn.addEventListener('click', async () => {
                const payload = {
                    cpu_threshold: parseFloat(document.getElementById('input-thresh-cpu').value),
                    memory_threshold: parseFloat(document.getElementById('input-thresh-mem').value),
                    storage_threshold: parseFloat(document.getElementById('input-thresh-disk').value),
                    network_threshold: parseFloat(document.getElementById('input-thresh-net').value),
                    spike_zscore: parseFloat(document.getElementById('input-thresh-zscore').value)
                };

                try {
                    const res = await fetch('/api/alerts/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const data = await res.json();
                    if (data.success) {
                        showToast('Alert thresholds saved successfully.', 'success');
                        document.getElementById('modal-alerts').classList.remove('active');
                        fetchTelemetryData();
                        fetchSpikesData();
                    }
                } catch (e) {
                    showToast('Failed to save thresholds.', 'error');
                }
            });
        }

        // File Drag and Drop handling
        setupFileUploadHandling();
    }

    function setupFileUploadHandling() {
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input-csv');
        const submitUploadBtn = document.getElementById('btn-submit-upload');
        const statusDisplay = document.getElementById('upload-status-display');
        const fileNameSpan = document.getElementById('selected-file-name');
        const fileSizeSpan = document.getElementById('selected-file-size');

        if (!dropZone || !fileInput) return;

        dropZone.addEventListener('click', () => fileInput.click());

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) handleSelectedFile(files[0]);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handleSelectedFile(e.target.files[0]);
        });

        function handleSelectedFile(file) {
            if (!file.name.toLowerCase().endsWith('.csv')) {
                showToast('Please select a valid CSV file.', 'error');
                return;
            }
            state.selectedUploadFile = file;
            fileNameSpan.textContent = file.name;
            fileSizeSpan.textContent = `${(file.size / 1024).toFixed(1)} KB`;
            statusDisplay.style.display = 'flex';
            submitUploadBtn.disabled = false;
        }

        submitUploadBtn.addEventListener('click', async () => {
            if (!state.selectedUploadFile) return;

            submitUploadBtn.disabled = true;
            submitUploadBtn.textContent = 'Uploading & Parsing...';

            const formData = new FormData();
            formData.append('file', state.selectedUploadFile);

            try {
                const res = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();

                if (res.ok && result.success) {
                    showToast(result.message, 'success');
                    document.getElementById('modal-upload').classList.remove('active');
                    state.selectedUploadFile = null;
                    statusDisplay.style.display = 'none';
                    fileInput.value = '';
                    fetchAllDashboardData();
                } else {
                    showToast(result.error || 'Failed to process CSV file.', 'error');
                }
            } catch (err) {
                showToast(`Upload failed: ${err.message}`, 'error');
            } finally {
                submitUploadBtn.disabled = false;
                submitUploadBtn.textContent = 'Process & Load Dataset';
            }
        });
    }

    // -------------------------------------------------------------
    // Data Fetching & Dashboard Refreshing
    // -------------------------------------------------------------
    async function fetchAllDashboardData() {
        await Promise.all([
            fetchTelemetryData(),
            fetchForecastData(),
            fetchSpikesData(),
            fetchValidationData(),
            fetchRecommendationsData()
        ]);
    }

    async function loadCurrentThresholdsIntoModal() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.thresholds) {
                document.getElementById('input-thresh-cpu').value = data.thresholds.cpu_threshold;
                document.getElementById('input-thresh-mem').value = data.thresholds.memory_threshold;
                document.getElementById('input-thresh-disk').value = data.thresholds.storage_threshold;
                document.getElementById('input-thresh-net').value = data.thresholds.network_threshold;
                document.getElementById('input-thresh-zscore').value = data.thresholds.spike_zscore;
            }
        } catch (e) {
            console.error('Error loading thresholds', e);
        }
    }

    // 1. Primary Telemetry & Cards
    async function fetchTelemetryData() {
        try {
            const res = await fetch('/api/metrics');
            const data = await res.json();

            // Update status indicators
            updateStatusIndicators(data);

            // Update Metric Cards
            updateMetricCards(data.summary);

            // Update Active Alerts Panel
            updateAlertsPanel(data.active_alerts);

            // Render Telemetry Timeline Chart
            renderTelemetryChart(data.series);

            // Render Dataset Preview Table
            renderPreviewTable(data.series);

        } catch (err) {
            console.error('Error fetching telemetry data', err);
        }
    }

    function updateStatusIndicators(data) {
        const modeText = document.getElementById('data-mode-text');
        const filenamePill = document.getElementById('dataset-filename-pill');
        const statusBadge = document.getElementById('data-status-badge');
        const demoBanner = document.getElementById('demo-banner');

        if (data.is_demo) {
            modeText.textContent = 'DEMO DATA ACTIVE';
            filenamePill.textContent = 'sample_cloud_metrics.csv';
            statusBadge.classList.remove('status-custom');
            if (demoBanner) demoBanner.style.display = 'flex';
        } else {
            modeText.textContent = 'CUSTOM CSV ACTIVE';
            filenamePill.textContent = data.filename || 'custom_dataset.csv';
            statusBadge.classList.add('status-custom');
            if (demoBanner) demoBanner.style.display = 'none';
        }
    }

    function updateMetricCards(summary) {
        if (!summary) return;

        // CPU
        document.getElementById('metric-cpu-current').textContent = `${summary.cpu.current}%`;
        document.getElementById('metric-cpu-mean').textContent = `${summary.cpu.mean}%`;
        document.getElementById('metric-cpu-max').textContent = `${summary.cpu.max}%`;
        document.getElementById('metric-cpu-min').textContent = `${summary.cpu.min}%`;
        document.getElementById('metric-cpu-bar').style.width = `${Math.min(summary.cpu.current, 100)}%`;
        const cpuStatus = document.getElementById('metric-cpu-status');
        if (summary.cpu.current >= 80) {
            cpuStatus.textContent = 'High Load';
            cpuStatus.className = 'metric-trend-badge badge-critical';
        } else {
            cpuStatus.textContent = 'Normal';
            cpuStatus.className = 'metric-trend-badge';
        }

        // Memory
        document.getElementById('metric-mem-current').textContent = `${summary.memory.current}%`;
        document.getElementById('metric-mem-mean').textContent = `${summary.memory.mean}%`;
        document.getElementById('metric-mem-max').textContent = `${summary.memory.max}%`;
        document.getElementById('metric-mem-min').textContent = `${summary.memory.min}%`;
        document.getElementById('metric-mem-bar').style.width = `${Math.min(summary.memory.current, 100)}%`;
        const memStatus = document.getElementById('metric-mem-status');
        if (summary.memory.current >= 80) {
            memStatus.textContent = 'Warning';
            memStatus.className = 'metric-trend-badge badge-warning';
        } else {
            memStatus.textContent = 'Healthy';
            memStatus.className = 'metric-trend-badge';
        }

        // Storage
        document.getElementById('metric-storage-current').textContent = `${summary.storage.current}%`;
        document.getElementById('metric-storage-mean').textContent = `${summary.storage.mean}%`;
        document.getElementById('metric-storage-max').textContent = `${summary.storage.max}%`;
        const headroom = Math.max(0, 100 - summary.storage.current).toFixed(1);
        document.getElementById('metric-storage-headroom').textContent = `${headroom}%`;
        document.getElementById('metric-storage-bar').style.width = `${Math.min(summary.storage.current, 100)}%`;

        // Network
        document.getElementById('metric-net-current').innerHTML = `${summary.network_in.current} <small>Mbps</small>`;
        document.getElementById('metric-net-egress').textContent = `${summary.network_out.current} Mbps`;
        document.getElementById('metric-net-max').textContent = `${summary.network_in.max} Mbps`;
        document.getElementById('metric-latency').textContent = `${summary.latency.current} ms`;
        const netPct = Math.min((summary.network_in.current / 1000) * 100, 100);
        document.getElementById('metric-net-bar').style.width = `${netPct}%`;
    }

    function updateAlertsPanel(alerts) {
        const container = document.getElementById('active-alerts-container');
        if (!container) return;

        if (!alerts || alerts.length === 0) {
            container.innerHTML = `
                <div class="alert-empty-state" style="color: var(--emerald-primary);">
                    ✓ All cloud metrics operating within safe operational thresholds.
                </div>`;
            return;
        }

        container.innerHTML = alerts.map(a => `
            <div class="alert-item ${a.severity === 'Warning' ? 'alert-warning' : ''}">
                <div class="alert-item-content">
                    <div class="alert-item-metric">
                        <span>${a.metric}</span>
                        <span class="badge-tag ${a.severity === 'Warning' ? 'badge-warning' : 'badge-critical'}">${a.severity}</span>
                    </div>
                    <div class="alert-item-text">${a.message}</div>
                </div>
            </div>
        `).join('');
    }

    function renderTelemetryChart(series) {
        const ctx = document.getElementById('chart-telemetry-timeline');
        if (!ctx || !series) return;

        if (state.charts.telemetry) {
            state.charts.telemetry.destroy();
        }

        const labels = series.timestamps.map(t => t.split(' ')[1] || t);
        const datasets = [];

        if (state.activeFilter === 'all' || state.activeFilter === 'cpu') {
            datasets.push({
                label: 'CPU Usage (%)',
                data: series.cpu,
                borderColor: '#06B6D4',
                backgroundColor: 'rgba(6, 182, 212, 0.08)',
                yAxisID: 'yPercent',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            });
        }

        if (state.activeFilter === 'all') {
            datasets.push({
                label: 'Memory Allocation (%)',
                data: series.memory,
                borderColor: '#A855F7',
                borderWidth: 2,
                yAxisID: 'yPercent',
                tension: 0.3,
                borderDash: [4, 4]
            });
            datasets.push({
                label: 'Storage (%)',
                data: series.storage,
                borderColor: '#10B981',
                borderWidth: 1.5,
                yAxisID: 'yPercent',
                tension: 0.1
            });
        }

        if (state.activeFilter === 'all' || state.activeFilter === 'network') {
            datasets.push({
                label: 'Network Ingress (Mbps)',
                data: series.network_in,
                borderColor: '#F59E0B',
                backgroundColor: 'rgba(245, 158, 11, 0.06)',
                yAxisID: 'yThroughput',
                borderWidth: 2,
                tension: 0.25,
                fill: true
            });
        }

        state.charts.telemetry = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { maxTicksLimit: 12 }
                    },
                    yPercent: {
                        type: 'linear',
                        position: 'left',
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        title: { display: true, text: 'Utilization (%)', color: '#94A3B8' }
                    },
                    yThroughput: {
                        type: 'linear',
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'Throughput (Mbps)', color: '#F59E0B' }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, usePointStyle: true }
                    }
                }
            }
        });
    }

    function renderPreviewTable(series) {
        const tbody = document.getElementById('tbody-raw-preview');
        if (!tbody || !series || !series.timestamps) return;

        const count = Math.min(series.timestamps.length, 12);
        let rowsHtml = '';

        for (let i = 0; i < count; i++) {
            rowsHtml += `
                <tr>
                    <td>${i + 1}</td>
                    <td>${series.timestamps[i]}</td>
                    <td><strong>${series.cpu[i]}%</strong></td>
                    <td>${series.memory[i]}%</td>
                    <td>${series.storage[i]}%</td>
                    <td>${series.network_in[i]}</td>
                    <td>${series.network_out[i]}</td>
                    <td>${series.latency ? series.latency[i] : '--'}</td>
                </tr>
            `;
        }

        tbody.innerHTML = rowsHtml;
    }

    // 2. Moving Average Forecasting (3, 5, 7)
    async function fetchForecastData() {
        try {
            const res = await fetch(`/api/predict?metric=${state.forecastMetric}`);
            const data = await res.json();

            // Update Next Step Projections
            document.getElementById('next-pred-ma3').textContent = `${data.next_prediction.ma_3}`;
            document.getElementById('next-pred-ma5').textContent = `${data.next_prediction.ma_5}`;
            document.getElementById('next-pred-ma7').textContent = `${data.next_prediction.ma_7}`;

            // Historical MAE comparison
            const mae3 = data.mae_summary.ma_3;
            const mae5 = data.mae_summary.ma_5;
            const mae7 = data.mae_summary.ma_7;
            const minMae = Math.min(mae3, mae5, mae7);
            let bestWin = '3';
            if (minMae === mae5) bestWin = '5';
            if (minMae === mae7) bestWin = '7';

            document.getElementById('best-mae-display').textContent = `MAE: ${minMae.toFixed(2)}`;
            document.getElementById('best-mae-label').textContent = `Optimal fit: MA-${bestWin} observation window`;

            // Render Chart
            renderForecastChart(data);

        } catch (err) {
            console.error('Error fetching forecast data', err);
        }
    }

    function renderForecastChart(data) {
        const ctx = document.getElementById('chart-moving-average');
        if (!ctx) return;

        if (state.charts.forecast) {
            state.charts.forecast.destroy();
        }

        const labels = data.timestamps.map(t => t.split(' ')[1] || t);
        const datasets = [
            {
                label: `Actual ${data.metric}`,
                data: data.actual,
                borderColor: '#FFFFFF',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 2,
                pointRadius: 3,
                pointBackgroundColor: '#FFFFFF',
                tension: 0.2
            }
        ];

        if (state.forecastWindow === '3' || state.forecastWindow === 'all') {
            datasets.push({
                label: 'MA-3 Observation Forecast',
                data: data.ma_3,
                borderColor: '#22D3EE',
                borderWidth: 2,
                borderDash: [5, 4],
                pointRadius: 0,
                tension: 0.3
            });
        }

        if (state.forecastWindow === '5' || state.forecastWindow === 'all') {
            datasets.push({
                label: 'MA-5 Observation Forecast',
                data: data.ma_5,
                borderColor: '#C084FC',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3
            });
        }

        if (state.forecastWindow === '7' || state.forecastWindow === 'all') {
            datasets.push({
                label: 'MA-7 Observation Forecast',
                data: data.ma_7,
                borderColor: '#FBBF24',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3
            });
        }

        state.charts.forecast = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { maxTicksLimit: 12 }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        title: { display: true, text: 'Value', color: '#94A3B8' }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, usePointStyle: true }
                    }
                }
            }
        });
    }

    // 3. CO3: Uncertain Network Traffic Prediction & Spike Detection
    async function fetchSpikesData() {
        try {
            const res = await fetch(`/api/spikes?metric=network_in_mbps&k_std=${state.spikeZScore}`);
            const data = await res.json();

            // Update stats
            document.getElementById('co3-spike-count').textContent = data.total_spikes;
            document.getElementById('co3-spike-percent').textContent = `${data.spike_percentage}% of timeline`;
            document.getElementById('co3-bandwidth-uncertainty').textContent = `${data.uncertainty_stats.average_bandwidth_uncertainty} Mbps`;
            document.getElementById('co3-volatility').textContent = `${data.uncertainty_stats.global_std_dev} Mbps`;

            // Max surge
            let maxExcess = 0;
            if (data.detected_spikes.length > 0) {
                maxExcess = Math.max(...data.detected_spikes.map(s => s.excess_mbps));
            }
            document.getElementById('co3-peak-surge').textContent = `+${maxExcess.toFixed(1)} Mbps`;

            // Render Table
            renderSpikesTable(data.detected_spikes);

            // Render Chart
            renderSpikesChart(data);

        } catch (err) {
            console.error('Error fetching spikes data', err);
        }
    }

    function renderSpikesTable(spikes) {
        const tbody = document.getElementById('tbody-spikes');
        if (!tbody) return;

        if (!spikes || spikes.length === 0) {
            tbody.innerHTML = `
                <tr><td colspan="7" class="text-center" style="color: var(--emerald-primary);">
                    ✓ No anomalous traffic surges detected at current ${state.spikeZScore}&sigma; threshold.
                </td></tr>`;
            return;
        }

        tbody.innerHTML = spikes.map(s => `
            <tr>
                <td>${s.timestamp}</td>
                <td><strong>${s.value} Mbps</strong></td>
                <td>${s.upper_bound} Mbps</td>
                <td style="color: #FB7185;">+${s.excess_mbps} Mbps</td>
                <td>${s.z_score}</td>
                <td><span class="badge-tag ${s.severity === 'Critical' ? 'badge-critical' : 'badge-warning'}">${s.severity}</span></td>
                <td><span class="subtle-pill">Auto-scale Ingress</span></td>
            </tr>
        `).join('');
    }

    function renderSpikesChart(data) {
        const ctx = document.getElementById('chart-spike-uncertainty');
        if (!ctx) return;

        if (state.charts.spikes) {
            state.charts.spikes.destroy();
        }

        const labels = data.timestamps.map(t => t.split(' ')[1] || t);

        // Build spike point scatter points
        const spikePoints = data.actual.map((val, idx) => {
            return data.is_spike[idx] ? val : null;
        });

        const datasets = [
            // Upper bound line
            {
                label: 'Upper Uncertainty Bound (+2σ)',
                data: data.upper_bound,
                borderColor: 'rgba(6, 182, 212, 0.45)',
                borderWidth: 1.5,
                borderDash: [4, 4],
                pointRadius: 0,
                fill: '+1', // Fill down to lower bound
                backgroundColor: 'rgba(6, 182, 212, 0.08)'
            },
            // Lower bound line
            {
                label: 'Lower Uncertainty Bound (-2σ)',
                data: data.lower_bound,
                borderColor: 'rgba(6, 182, 212, 0.25)',
                borderWidth: 1,
                borderDash: [4, 4],
                pointRadius: 0,
                fill: false
            },
            // Baseline moving average
            {
                label: 'Expected Baseline (MA-5)',
                data: data.baseline_prediction,
                borderColor: '#06B6D4',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3
            },
            // Observed network ingress
            {
                label: 'Observed Network Ingress (Mbps)',
                data: data.actual,
                borderColor: '#38BDF8',
                backgroundColor: 'transparent',
                borderWidth: 2.2,
                pointRadius: 2,
                tension: 0.15
            },
            // Anomalous spikes scatter
            {
                label: 'Detected Traffic Spike Anomaly',
                data: spikePoints,
                borderColor: '#F43F5E',
                backgroundColor: '#F43F5E',
                borderWidth: 2,
                pointRadius: 7,
                pointHoverRadius: 9,
                showLine: false,
                pointStyle: 'triangle'
            }
        ];

        state.charts.spikes = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { maxTicksLimit: 12 }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        title: { display: true, text: 'Ingress Throughput (Mbps)', color: '#94A3B8' }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12, usePointStyle: true }
                    }
                }
            }
        });
    }

    // 4. CO5: Chronological Model Validation (MAE vs RMSE)
    async function fetchValidationData() {
        try {
            const res = await fetch(`/api/validation?metric=network_in_mbps&train_ratio=${state.trainRatio}`);
            const data = await res.json();

            // Update Summary
            document.getElementById('val-total-samples').textContent = data.total_samples;
            document.getElementById('val-train-samples').textContent = data.train_samples;
            document.getElementById('val-test-samples').textContent = data.test_samples;
            document.getElementById('val-split-time').textContent = data.split_timestamp;

            // Update Scorecard table
            const tbody = document.getElementById('tbody-validation-scorecard');
            const models = data.models;
            let rows = '';

            for (const key of ['MA_3', 'MA_5', 'MA_7']) {
                const m = models[key];
                const isBest = data.best_model === key;
                rows += `
                    <tr class="${isBest ? 'highlight-row' : ''}">
                        <td><strong>Moving Average (Window ${m.window})</strong></td>
                        <td class="cyan-glow">${m.mae} Mbps</td>
                        <td class="purple-glow">${m.rmse} Mbps</td>
                        <td>
                            ${isBest 
                                ? '<span class="badge-tag badge-optimal">Recommended (Lowest MAE)</span>' 
                                : '<span class="badge-tag badge-subtle">Baseline</span>'}
                        </td>
                    </tr>
                `;
            }
            tbody.innerHTML = rows;

            // Render Error Comparison Chart
            renderValidationChart(models);

        } catch (err) {
            console.error('Error fetching validation data', err);
        }
    }

    function renderValidationChart(models) {
        const ctx = document.getElementById('chart-validation-comparison');
        if (!ctx) return;

        if (state.charts.validation) {
            state.charts.validation.destroy();
        }

        const labels = ['MA-3 Window', 'MA-5 Window', 'MA-7 Window'];
        const maeData = [models.MA_3.mae, models.MA_5.mae, models.MA_7.mae];
        const rmseData = [models.MA_3.rmse, models.MA_5.rmse, models.MA_7.rmse];

        state.charts.validation = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'MAE (Mean Absolute Error)',
                        data: maeData,
                        backgroundColor: 'rgba(6, 182, 212, 0.75)',
                        borderColor: '#06B6D4',
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: 'RMSE (Root Mean Squared Error)',
                        data: rmseData,
                        backgroundColor: 'rgba(168, 85, 247, 0.75)',
                        borderColor: '#A855F7',
                        borderWidth: 1,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        title: { display: true, text: 'Loss Magnitude (Mbps)', color: '#94A3B8' }
                    }
                },
                plugins: {
                    legend: { position: 'top' }
                }
            }
        });
    }

    // 5. AI Resource Scaling Recommendations
    async function fetchRecommendationsData() {
        try {
            const res = await fetch('/api/recommendations');
            const data = await res.json();
            const container = document.getElementById('recommendations-container');
            if (!container) return;

            if (!data.recommendations || data.recommendations.length === 0) {
                container.innerHTML = `<div class="alert-empty-state">No scaling actions required at this time.</div>`;
                return;
            }

            container.innerHTML = data.recommendations.map(r => `
                <div class="rec-item">
                    <div class="rec-header-row">
                        <span class="rec-title">${r.type}</span>
                        <span class="rec-badge ${
                            r.severity === 'Critical' ? 'badge-critical' :
                            r.severity === 'High' ? 'badge-warning' :
                            r.severity === 'Medium' ? 'badge-warning' : 'badge-optimal'
                        }">${r.badge}</span>
                    </div>
                    <div class="rec-action">${r.action}</div>
                    <div class="rec-impact">${r.rationale} &bull; <em>${r.impact}</em></div>
                </div>
            `).join('');

        } catch (err) {
            console.error('Error fetching recommendations', err);
        }
    }

    // -------------------------------------------------------------
    // Toast Notification Utility
    // -------------------------------------------------------------
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span>${type === 'success' ? '✓' : type === 'error' ? '⚠' : 'ℹ'}</span>
            <span>${message}</span>
        `;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(15px)';
            setTimeout(() => toast.remove(), 300);
        }, 3800);
    }

});
