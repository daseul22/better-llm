"""Tests for database utility functions."""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.storage.db_utils import (
    DatabaseExecutor,
    execute_single_query,
    execute_single_update
)
from src.domain.exceptions import StorageError


class TestDatabaseExecutor:
    """DatabaseExecutor 클래스 테스트."""

    def test_context_manager_success(self, tmp_path):
        """정상 실행 시 Connection 생명주기 검증."""
        db_path = tmp_path / "test.db"

        with DatabaseExecutor(db_path) as executor:
            assert executor.conn is not None
            assert executor.cursor is not None

        # Context 종료 후 Connection 닫힘 검증 불가 (이미 닫혔으므로)
        # 단순히 예외가 발생하지 않음을 검증

    def test_context_manager_exception_rollback(self, tmp_path):
        """예외 발생 시 Rollback 검증."""
        db_path = tmp_path / "test.db"

        with pytest.raises(StorageError):
            with DatabaseExecutor(db_path) as executor:
                executor.execute_query("INVALID SQL")

    def test_execute_query_success(self, tmp_path):
        """SELECT 쿼리 정상 실행."""
        db_path = tmp_path / "test.db"

        # Setup
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice')")
        conn.commit()
        conn.close()

        # Test
        with DatabaseExecutor(db_path) as executor:
            rows = executor.execute_query("SELECT * FROM test WHERE id = ?", (1,))
            assert len(rows) == 1
            assert rows[0]["name"] == "Alice"

    def test_execute_query_empty_result(self, tmp_path):
        """SELECT 쿼리 결과 없음."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        with DatabaseExecutor(db_path) as executor:
            rows = executor.execute_query("SELECT * FROM test")
            assert len(rows) == 0

    def test_execute_query_error(self, tmp_path):
        """SELECT 쿼리 실행 실패."""
        db_path = tmp_path / "test.db"

        with pytest.raises(StorageError):
            with DatabaseExecutor(db_path) as executor:
                executor.execute_query("SELECT * FROM nonexistent_table")

    def test_execute_query_no_cursor(self, tmp_path):
        """Cursor 없이 쿼리 실행 시도."""
        db_path = tmp_path / "test.db"
        executor = DatabaseExecutor(db_path)

        with pytest.raises(StorageError, match="cursor not initialized"):
            executor.execute_query("SELECT 1")

    def test_execute_update_insert(self, tmp_path):
        """INSERT 쿼리 정상 실행."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.commit()
        conn.close()

        with DatabaseExecutor(db_path) as executor:
            rowcount = executor.execute_update(
                "INSERT INTO test VALUES (?, ?)",
                (1, "Alice"),
                operation="insert test"
            )
            assert rowcount == 1

    def test_execute_update_update(self, tmp_path):
        """UPDATE 쿼리 정상 실행."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice')")
        conn.commit()
        conn.close()

        with DatabaseExecutor(db_path) as executor:
            rowcount = executor.execute_update(
                "UPDATE test SET name = ? WHERE id = ?",
                ("Bob", 1),
                operation="update test"
            )
            assert rowcount == 1

    def test_execute_update_delete(self, tmp_path):
        """DELETE 쿼리 정상 실행."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        conn.close()

        with DatabaseExecutor(db_path) as executor:
            rowcount = executor.execute_update(
                "DELETE FROM test WHERE id = ?",
                (1,),
                operation="delete test"
            )
            assert rowcount == 1

    def test_execute_update_no_rows(self, tmp_path):
        """UPDATE/DELETE가 0행에 영향."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        with DatabaseExecutor(db_path) as executor:
            rowcount = executor.execute_update(
                "DELETE FROM test WHERE id = ?",
                (999,)
            )
            assert rowcount == 0

    def test_execute_update_error(self, tmp_path):
        """UPDATE 쿼리 실행 실패."""
        db_path = tmp_path / "test.db"

        with pytest.raises(StorageError):
            with DatabaseExecutor(db_path) as executor:
                executor.execute_update("UPDATE nonexistent_table SET x = 1")

    def test_execute_update_no_cursor(self, tmp_path):
        """Cursor 없이 UPDATE 실행 시도."""
        db_path = tmp_path / "test.db"
        executor = DatabaseExecutor(db_path)

        with pytest.raises(StorageError, match="cursor not initialized"):
            executor.execute_update("INSERT INTO test VALUES (1)")


class TestConvenienceFunctions:
    """편의 함수 테스트."""

    def test_execute_single_query_success(self, tmp_path):
        """execute_single_query() 정상 실행."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        conn.close()

        rows = execute_single_query(
            db_path,
            "SELECT * FROM test",
            operation="test query"
        )
        assert len(rows) == 1

    def test_execute_single_query_with_params(self, tmp_path):
        """execute_single_query() with params."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice')")
        conn.execute("INSERT INTO test VALUES (2, 'Bob')")
        conn.commit()
        conn.close()

        rows = execute_single_query(
            db_path,
            "SELECT * FROM test WHERE name = ?",
            ("Alice",)
        )
        assert len(rows) == 1
        assert rows[0]["id"] == 1

    def test_execute_single_query_error(self, tmp_path):
        """execute_single_query() 실행 실패."""
        db_path = tmp_path / "test.db"

        with pytest.raises(StorageError):
            execute_single_query(db_path, "SELECT * FROM nonexistent")

    def test_execute_single_update_success(self, tmp_path):
        """execute_single_update() 정상 실행."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        rowcount = execute_single_update(
            db_path,
            "INSERT INTO test VALUES (?)",
            (1,),
            operation="insert test"
        )
        assert rowcount == 1

    def test_execute_single_update_with_params(self, tmp_path):
        """execute_single_update() with params."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice')")
        conn.commit()
        conn.close()

        rowcount = execute_single_update(
            db_path,
            "UPDATE test SET name = ? WHERE id = ?",
            ("Bob", 1)
        )
        assert rowcount == 1

    def test_execute_single_update_error(self, tmp_path):
        """execute_single_update() 실행 실패."""
        db_path = tmp_path / "test.db"

        with pytest.raises(StorageError):
            execute_single_update(db_path, "INSERT INTO nonexistent VALUES (1)")


class TestLoggingBehavior:
    """로깅 동작 테스트."""

    @patch("src.infrastructure.storage.db_utils.logger")
    def test_execute_query_logs_debug(self, mock_logger, tmp_path):
        """execute_query() 디버그 로깅."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        with DatabaseExecutor(db_path) as executor:
            executor.execute_query("SELECT * FROM test", operation="test_op")

        assert mock_logger.debug.call_count >= 2
        mock_logger.debug.assert_any_call("Executing test_op: SELECT * FROM test...")

    @patch("src.infrastructure.storage.db_utils.logger")
    def test_execute_query_logs_error(self, mock_logger, tmp_path):
        """execute_query() 에러 로깅."""
        db_path = tmp_path / "test.db"

        with pytest.raises(StorageError):
            with DatabaseExecutor(db_path) as executor:
                executor.execute_query("SELECT * FROM nonexistent", operation="test_op")

        mock_logger.error.assert_called_once()
        assert "Database error during test_op" in str(mock_logger.error.call_args)
