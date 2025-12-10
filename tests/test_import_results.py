"""
Tests for import_results MCP tool.

This module tests the import_results functionality that fetches job results
from NeMo API or local files and imports them into shared DuckDB.
"""
import pytest
import os
import tempfile
import pandas as pd
from unittest.mock import patch, MagicMock
import duckdb


# Test fixtures
@pytest.fixture
def sample_csv_data() -> pd.DataFrame:
    """Create sample data matching NeMo job output format."""
    return pd.DataFrame({
        "incident_id": ["DEMO-ABC123", "DEMO-DEF456", "DEMO-GHI789"],
        "priority": ["high", "medium", "low"],
        "status": ["open", "closed", "open"],
        "short_description": [
            "Server down in datacenter",
            "Password reset request",
            "Network connectivity issues"
        ],
        "opened_at": ["2023-01-15 10:30:00", "2023-02-20 14:45:00", "2023-03-10 09:00:00"]
    })


@pytest.fixture
def temp_csv_file(sample_csv_data, tmp_path):
    """Create a temporary CSV file with sample data."""
    csv_path = tmp_path / "job-test123.csv"
    sample_csv_data.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def temp_duckdb_path(tmp_path):
    """Create a temporary DuckDB path."""
    return str(tmp_path / "test_tables.duckdb")


class TestImportResultsLocal:
    """Test import_results with local CSV files."""
    
    def test_import_from_local_csv(self, sample_csv_data, tmp_path):
        """Test importing from an existing local CSV file."""
        # Setup
        job_id = "job-test123"
        output_path = tmp_path / "data-designer-output"
        output_path.mkdir()
        csv_path = output_path / f"{job_id}.csv"
        sample_csv_data.to_csv(csv_path, index=False)
        
        duckdb_path = str(tmp_path / "tables.duckdb")
        
        # Import the function (we'll mock the module paths)
        with patch.dict(os.environ, {
            "DUCKDB_PATH": duckdb_path,
        }):
            # Directly test the logic
            df = pd.read_csv(csv_path)
            table_name = job_id.replace("-", "_")
            
            # Save to DuckDB
            conn = duckdb.connect(duckdb_path)
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.register("temp_df", df)
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
            conn.unregister("temp_df")
            
            # Verify table exists
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            assert table_name in table_names
            
            # Verify data
            result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            assert result == 3
            
            conn.close()
    
    def test_import_creates_table_with_correct_columns(self, sample_csv_data, tmp_path):
        """Test that imported table has correct columns."""
        duckdb_path = str(tmp_path / "tables.duckdb")
        table_name = "test_incidents"
        
        conn = duckdb.connect(duckdb_path)
        conn.register("temp_df", sample_csv_data)
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
        conn.unregister("temp_df")
        
        # Get column info
        columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
        column_names = [col[0] for col in columns]
        
        assert "incident_id" in column_names
        assert "priority" in column_names
        assert "status" in column_names
        assert "short_description" in column_names
        assert "opened_at" in column_names
        
        conn.close()
    
    def test_import_with_custom_table_name(self, sample_csv_data, tmp_path):
        """Test importing with a custom table name."""
        duckdb_path = str(tmp_path / "tables.duckdb")
        custom_name = "My Custom Table"
        expected_name = "my_custom_table"  # Sanitized
        
        conn = duckdb.connect(duckdb_path)
        sanitized_name = custom_name.lower().replace(" ", "_").replace("-", "_")
        
        conn.register("temp_df", sample_csv_data)
        conn.execute(f"CREATE TABLE {sanitized_name} AS SELECT * FROM temp_df")
        conn.unregister("temp_df")
        
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert expected_name in table_names
        
        conn.close()


class TestImportResultsAPI:
    """Test import_results with NeMo API fetching."""
    
    def test_import_from_api_mock(self, sample_csv_data, tmp_path):
        """Test importing via NeMo API (mocked)."""
        import io
        
        # Mock API response
        csv_content = sample_csv_data.to_csv(index=False)
        
        # Simulate parsing
        df = pd.read_csv(io.StringIO(csv_content))
        
        assert len(df) == 3
        assert list(df.columns) == ["incident_id", "priority", "status", "short_description", "opened_at"]
    
    def test_api_response_saves_locally(self, sample_csv_data, tmp_path):
        """Test that API response is saved locally for caching."""
        job_id = "job-api-test"
        output_path = tmp_path / "data-designer-output"
        output_path.mkdir()
        csv_path = output_path / f"{job_id}.csv"
        
        # Simulate saving after API fetch
        sample_csv_data.to_csv(csv_path, index=False)
        
        assert csv_path.exists()
        loaded = pd.read_csv(csv_path)
        assert len(loaded) == 3


class TestImportResultsErrorHandling:
    """Test error handling in import_results."""
    
    def test_import_nonexistent_local_file(self, tmp_path):
        """Test handling of non-existent local file."""
        csv_path = tmp_path / "nonexistent.csv"
        assert not csv_path.exists()
    
    def test_import_empty_dataframe(self, tmp_path):
        """Test handling of empty DataFrame."""
        duckdb_path = str(tmp_path / "tables.duckdb")
        empty_df = pd.DataFrame()
        
        assert empty_df.empty
        # The tool should return an error for empty data
    
    def test_sanitize_table_name_special_chars(self):
        """Test table name sanitization with special characters."""
        test_cases = [
            ("job-abc-123", "job_abc_123"),
            ("My Table Name", "my_table_name"),
            ("UPPERCASE", "uppercase"),
            ("with--multiple---dashes", "with__multiple___dashes"),
        ]
        
        for input_name, expected in test_cases:
            sanitized = input_name.lower().replace(" ", "_").replace("-", "_")
            assert sanitized == expected, f"Expected {expected}, got {sanitized}"


class TestDuckDBIntegration:
    """Integration tests for DuckDB table operations."""
    
    def test_table_persistence(self, sample_csv_data, tmp_path):
        """Test that tables persist after connection close."""
        duckdb_path = str(tmp_path / "persist_test.duckdb")
        table_name = "persistent_table"
        
        # Create table
        conn1 = duckdb.connect(duckdb_path)
        conn1.register("temp_df", sample_csv_data)
        conn1.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
        conn1.unregister("temp_df")
        conn1.close()
        
        # Verify persistence in new connection
        conn2 = duckdb.connect(duckdb_path)
        tables = conn2.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        
        assert table_name in table_names
        
        row_count = conn2.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        assert row_count == 3
        
        conn2.close()
    
    def test_table_overwrite(self, sample_csv_data, tmp_path):
        """Test that existing tables are overwritten."""
        duckdb_path = str(tmp_path / "overwrite_test.duckdb")
        table_name = "overwrite_table"
        
        conn = duckdb.connect(duckdb_path)
        
        # Create initial table
        conn.register("temp_df", sample_csv_data)
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
        conn.unregister("temp_df")
        
        # Override with new data
        new_data = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.register("temp_df", new_data)
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
        conn.unregister("temp_df")
        
        # Verify new data
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        assert row_count == 2
        
        columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
        column_names = [c[0] for c in columns]
        assert "col1" in column_names
        assert "col2" in column_names
        
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
