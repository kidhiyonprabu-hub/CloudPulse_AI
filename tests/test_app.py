"""
Automated Test Suite for CloudPulse AI
Framework: Python unittest
Verifies routes, mathematical forecasting (Moving Averages),
CO3 uncertainty spike detection, CO5 chronological model validation (MAE/RMSE),
and CSV upload/export capabilities.
"""

import io
import json
import os
import unittest
import pandas as pd
import numpy as np

from app import (
    app,
    CURRENT_STATE,
    initialize_runtime,
    calculate_moving_average_forecast,
    compute_uncertainty_and_spikes,
    perform_chronological_validation,
    generate_scaling_recommendations
)


class CloudPulseAITestCase(unittest.TestCase):

    def setUp(self):
        """Prepare Flask test client and reset state."""
        app.config['TESTING'] = True
        self.client = app.test_client()
        initialize_runtime()

    def test_01_index_page(self):
        """Verify dashboard index route loads successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('CloudPulse', content)
        self.assertIn('DEMO DATA ACTIVE', content)
        self.assertIn('CO3', content)
        self.assertIn('CO5', content)

    def test_02_api_status(self):
        """Verify status API returns healthy state with demo metadata."""
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertTrue(data['is_demo'])
        self.assertGreater(data['records_count'], 0)
        self.assertIn('cpu_threshold', data['thresholds'])

    def test_03_api_metrics(self):
        """Verify telemetry metrics endpoint returns summary and series data."""
        response = self.client.get('/api/metrics')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('summary', data)
        self.assertIn('series', data)
        self.assertIn('cpu', data['summary'])
        self.assertIn('memory', data['summary'])
        self.assertIn('network_in', data['summary'])
        self.assertIn('storage', data['summary'])
        self.assertGreater(len(data['series']['timestamps']), 0)

    def test_04_moving_average_logic(self):
        """Verify step-ahead Moving Average calculation has no lookahead bias."""
        series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        ma_3 = calculate_moving_average_forecast(series, window=3)
        # Shift(1) rolling mean with window=3:
        # index 0: NaN
        # index 1: NaN
        # index 2: NaN
        # index 3: mean(10, 20, 30) = 20.0
        # index 4: mean(20, 30, 40) = 30.0
        self.assertTrue(np.isnan(ma_3.iloc[0]))
        self.assertTrue(np.isnan(ma_3.iloc[1]))
        self.assertTrue(np.isnan(ma_3.iloc[2]))
        self.assertAlmostEqual(ma_3.iloc[3], 20.0)
        self.assertAlmostEqual(ma_3.iloc[4], 30.0)

    def test_05_api_predict(self):
        """Verify prediction endpoint returns MA-3, MA-5, MA-7 and next forecast."""
        response = self.client.get('/api/predict?metric=cpu_usage')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['metric'], 'cpu_usage')
        self.assertIn('ma_3', data)
        self.assertIn('ma_5', data)
        self.assertIn('ma_7', data)
        self.assertIn('next_prediction', data)
        self.assertIn('mae_summary', data)
        self.assertGreater(data['next_prediction']['ma_3'], 0)

    def test_06_co3_uncertainty_and_spikes(self):
        """Verify CO3 network traffic uncertainty corridor and spike detection."""
        response = self.client.get('/api/spikes?metric=network_in_mbps&k_std=2.0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('upper_bound', data)
        self.assertIn('lower_bound', data)
        self.assertIn('detected_spikes', data)
        self.assertIn('uncertainty_stats', data)
        
        # In sample demo dataset, there should be injected network spikes
        self.assertGreater(data['total_spikes'], 0)
        for spike in data['detected_spikes']:
            self.assertGreater(spike['value'], spike['upper_bound'])
            self.assertGreaterEqual(spike['z_score'], 1.5)

    def test_07_co5_chronological_validation(self):
        """Verify CO5 chronological train/test split and non-negative MAE/RMSE."""
        response = self.client.get('/api/validation?metric=network_in_mbps&train_ratio=0.75')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['train_ratio'], 0.75)
        self.assertGreater(data['train_samples'], 0)
        self.assertGreater(data['test_samples'], 0)
        self.assertEqual(data['total_samples'], data['train_samples'] + data['test_samples'])

        # Verify models
        for win in ['MA_3', 'MA_5', 'MA_7']:
            self.assertIn(win, data['models'])
            model_eval = data['models'][win]
            self.assertGreaterEqual(model_eval['mae'], 0.0)
            self.assertGreaterEqual(model_eval['rmse'], 0.0)
            # Mathematical property: RMSE >= MAE
            self.assertGreaterEqual(round(model_eval['rmse'], 2), round(model_eval['mae'], 2) - 0.01)

        self.assertIn(data['best_model'], ['MA_3', 'MA_5', 'MA_7'])

    def test_08_scaling_recommendations(self):
        """Verify AI rule-based scaling recommendations generation."""
        response = self.client.get('/api/recommendations')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('recommendations', data)
        self.assertGreater(len(data['recommendations']), 0)
        first_rec = data['recommendations'][0]
        self.assertIn('action', first_rec)
        self.assertIn('severity', first_rec)
        self.assertIn('rationale', first_rec)

    def test_09_alert_configuration(self):
        """Verify updating alert thresholds via POST."""
        payload = {
            'cpu_threshold': 88.0,
            'memory_threshold': 85.0,
            'network_threshold': 750.0
        }
        response = self.client.post('/api/alerts/config',
                                  data=json.dumps(payload),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['thresholds']['cpu_threshold'], 88.0)
        self.assertEqual(data['thresholds']['memory_threshold'], 85.0)

    def test_10_csv_upload_valid(self):
        """Verify uploading custom CSV dataset."""
        csv_content = """timestamp,cpu_usage,memory_usage,storage_usage,network_in_mbps,network_out_mbps,latency_ms
2026-10-10 12:00:00,45.0,60.0,40.0,150.0,120.0,20.0
2026-10-10 12:05:00,48.0,61.0,40.0,160.0,125.0,21.0
2026-10-10 12:10:00,52.0,62.0,40.1,170.0,130.0,22.0
2026-10-10 12:15:00,55.0,63.0,40.1,180.0,135.0,23.0
2026-10-10 12:20:00,58.0,64.0,40.2,190.0,140.0,24.0
2026-10-10 12:25:00,60.0,65.0,40.2,200.0,145.0,25.0
"""
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_upload.csv')
        }
        response = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertTrue(result['success'])
        self.assertEqual(result['records_count'], 6)
        self.assertEqual(CURRENT_STATE['is_demo'], False)

    def test_11_csv_upload_invalid(self):
        """Verify uploading invalid payload returns proper error."""
        # Non-csv extension
        data = {
            'file': (io.BytesIO(b"dummy data"), 'test.txt')
        }
        response = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)

        # Empty file
        response = self.client.post('/api/upload', data={}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)

    def test_12_reset_demo(self):
        """Verify resetting to demo dataset."""
        response = self.client.post('/api/reset-demo')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertTrue(CURRENT_STATE['is_demo'])

    def test_13_export_report_and_sample_download(self):
        """Verify report generation and sample CSV download endpoints."""
        export_res = self.client.get('/api/export-report')
        self.assertEqual(export_res.status_code, 200)
        self.assertIn('text/csv', export_res.content_type)
        self.assertIn('attachment;', export_res.headers.get('Content-Disposition', ''))

        sample_res = self.client.get('/api/sample-download')
        self.assertEqual(sample_res.status_code, 200)
        self.assertIn('text/csv', sample_res.content_type)
        sample_res.close()
        export_res.close()


if __name__ == '__main__':
    unittest.main()
