import unittest
from unittest.mock import MagicMock, patch
from mcp_server_py.client import NemoDataDesignerClient
from mcp_server_py.models import SubmitJobRequest

class TestClient(unittest.TestCase):
    @patch("httpx.Client")
    def test_submit_job_success(self, mock_client_cls):
        # Setup Mock
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        # Mock responses
        mock_submit_resp = MagicMock()
        mock_submit_resp.json.return_value = {"id": "job-123", "status": "pending"}
        mock_submit_resp.raise_for_status.return_value = None

        mock_poll_success = MagicMock()
        mock_poll_success.json.return_value = {"status": "success"}

        mock_result_resp = MagicMock()
        mock_result_resp.text = '{"col1": "val1"}\n{"col1": "val2"}'
        mock_result_resp.raise_for_status.return_value = None

        mock_instance.post.return_value = mock_submit_resp
        
        def side_effect_get(url):
            if "jobs/job-123/results" in url:
                return mock_result_resp
            elif "jobs/job-123" in url:
                return mock_poll_success
            return MagicMock()

        mock_instance.get.side_effect = side_effect_get

        # Create Request
        req = SubmitJobRequest(
            job_name="test-job",
            model_configs=[],
            column_configs=[],
            num_samples=10
        )

        client = NemoDataDesignerClient()
        response = client.submit_job(req)

        self.assertEqual(response.job_id, "job-123")
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["col1"], "val1")


    @patch("httpx.Client")
    def test_download_parquet_support(self, mock_client_cls):
        """Test that the client correctly unpacks a tar.gz containing parquet."""
        import io
        import tarfile
        import pandas as pd
        
        # 1. Create a dummy dataframe and save to parquet in memory
        df = pd.DataFrame({"topic": ["Laptop"], "review": ["Great!"]})
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer)
        parquet_buffer.seek(0)
        
        # 2. Create a tar.gz containing that parquet file in memory
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="test.parquet")
            info.size = len(parquet_buffer.getvalue())
            parquet_buffer.seek(0)
            tar.addfile(info, parquet_buffer)
        
        tar_bytes = tar_buffer.getvalue()

        # 3. Mock Response
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        
        mock_resp = MagicMock()
        mock_resp.content = tar_bytes
        mock_resp.raise_for_status.return_value = None
        
        mock_instance.get.return_value = mock_resp
        
        # 4. Run Client
        client = NemoDataDesignerClient()
        data = client.download_dataset("job-123")
        
        # 5. Assertions
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["topic"], "Laptop")
        self.assertEqual(data[0]["topic"], "Laptop")
        self.assertEqual(data[0]["review"], "Great!")

    @patch("httpx.Client")
    def test_job_management_methods(self, mock_client_cls):
        """Test status, logs, cancel, and preview methods."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        
        client = NemoDataDesignerClient()

        # 1. Test get_job_status
        mock_status_resp = MagicMock()
        mock_status_resp.json.return_value = {"status": "running"}
        mock_status_resp.raise_for_status.return_value = None
        mock_instance.get.return_value = mock_status_resp
        
        status = client.get_job_status("job-123")
        self.assertEqual(status, "running")
        mock_instance.get.assert_called_with("http://localhost:8080/v1/data-designer/jobs/job-123/status")
        
        # 2. Test get_job_logs
        mock_logs_resp = MagicMock()
        # logs format: {"data": [{"message": "log line 1"}, ...]}
        mock_logs_resp.json.return_value = {"data": [{"message": "Started"}, {"message": "Processing"}]}
        mock_logs_resp.raise_for_status.return_value = None
        mock_instance.get.return_value = mock_logs_resp # update return value
        
        logs = client.get_job_logs("job-123")
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0], "Started")
        
        # 3. Test cancel_job
        mock_cancel_resp = MagicMock()
        mock_cancel_resp.json.return_value = {"id": "job-123", "status": "cancelled"}
        mock_cancel_resp.raise_for_status.return_value = None
        mock_instance.post.return_value = mock_cancel_resp
        
        res = client.cancel_job("job-123")
        self.assertEqual(res["status"], "cancelled")
        mock_instance.post.assert_called_with("http://localhost:8080/v1/data-designer/jobs/job-123/cancel")

        # 4. Test preview_job
        mock_preview_resp = MagicMock()
        # Preview returns JSONL text
        mock_preview_resp.text = '{"col1": "val1"}\n{"col1": "val2"}'
        mock_preview_resp.raise_for_status.return_value = None
        mock_instance.post.return_value = mock_preview_resp
        
        req = SubmitJobRequest(job_name="preview", model_configs=[], column_configs=[])
        records = client.preview_job(req)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["col1"], "val1")

if __name__ == "__main__":
    unittest.main()
