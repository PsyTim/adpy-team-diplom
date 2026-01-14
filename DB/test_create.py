# import unittest
from unittest.mock import patch, mock_open, MagicMock
from create import recreate_tables


class TestRecreateTables(unittest.TestCase):
    @patch("create.connect")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="CREATE TABLE test (id SERIAL PRIMARY KEY);",
    )
    def test_recreate_tables(self, mock_file, mock_connect):
        # Mock the database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Call the function
        recreate_tables("test_path/")

        # Assert the file was opened with the correct path
        mock_file.assert_called_once_with("test_path/create.sql", "r", encoding="utf-8")

        # Assert the SQL was executed
        mock_cursor.execute.assert_called_once_with(
            "CREATE TABLE test (id SERIAL PRIMARY KEY);"
        )

        # Assert the connection and cursor were used correctly
        mock_conn.cursor.assert_called_once()
        mock_conn.__enter__.assert_called_once()
        mock_conn.__exit__.assert_called_once()
        mock_cursor.__enter__.assert_called_once()
        mock_cursor.__exit__.assert_called_once()

    @patch("create.connect")
    @patch("builtins.open", new_callable=mock_open)
    def test_recreate_tables_file_not_found(self, mock_file, mock_connect):
        # Simulate FileNotFoundError
        mock_file.side_effect = FileNotFoundError

        # Call the function and assert it raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            recreate_tables("test_path/")

    @patch("create.connect")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="CREATE TABLE test (id SERIAL PRIMARY KEY);",
    )
    def test_recreate_tables_sql_execution_error(self, mock_file, mock_connect):
        # Mock the database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Simulate an error during SQL execution
        mock_cursor.execute.side_effect = Exception("SQL execution error")

        # Call the function and assert it raises the exception
        with self.assertRaises(Exception):
            recreate_tables("test_path/")

        # Assert the file was opened
        mock_file.assert_called_once_with("test_path/create.sql", "r", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
