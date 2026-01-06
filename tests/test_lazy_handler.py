# VIBE-CODED
"""Tests for LazyHandler to ensure thread-safety and correct behavior."""

import logging
import tempfile
import threading
import time
from pathlib import Path

import pytest

from pfund_kit.logging.handlers import LazyHandler


class TestLazyHandler:
    """Test suite for LazyHandler."""

    def test_file_not_created_until_first_log(self):
        """Test that log file is not created until first log message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test.log'

            # Create lazy handler
            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
            )

            # File should not exist yet
            assert not log_path.exists(), "Log file created prematurely"

            # Emit a log record
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test message',
                args=(),
                exc_info=None,
            )
            handler.emit(record)

            # File should now exist
            assert log_path.exists(), "Log file not created after emit"

            handler.close()

    def test_thread_safety_multiple_threads(self):
        """Test that multiple threads don't create multiple handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_threaded.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
            )

            # Track handler creation
            handlers_created = []
            original_ensure = handler._ensure_target_handler

            def tracked_ensure():
                result = original_ensure()
                handlers_created.append(result)
                return result

            handler._ensure_target_handler = tracked_ensure

            # Create multiple threads that try to log simultaneously
            def log_message(msg_id):
                record = logging.LogRecord(
                    name='test',
                    level=logging.INFO,
                    pathname='test.py',
                    lineno=1,
                    msg=f'Message {msg_id}',
                    args=(),
                    exc_info=None,
                )
                handler.emit(record)

            threads = [threading.Thread(target=log_message, args=(i,)) for i in range(10)]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            # All handler instances should be the same object
            unique_handlers = set(id(h) for h in handlers_created)
            assert len(unique_handlers) == 1, f"Multiple handlers created: {len(unique_handlers)}"

            handler.close()

    def test_formatter_applied_to_target(self):
        """Test that formatter is applied to the target handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_formatter.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
            )

            # Set formatter before first emit
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)

            # Emit a record
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test message',
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            handler.flush()

            # Check that formatter was applied
            with open(log_path) as f:
                content = f.read()
                assert 'INFO: Test message' in content

            handler.close()

    def test_filters_applied_to_target(self):
        """Test that filters are applied to the target handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_filter.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
            )

            # Add filter that blocks all DEBUG messages
            class DebugFilter(logging.Filter):
                def filter(self, record):
                    return record.levelno > logging.DEBUG

            handler.addFilter(DebugFilter())

            # Handle DEBUG record (should be filtered) - use handle() not emit()
            debug_record = logging.LogRecord(
                name='test',
                level=logging.DEBUG,
                pathname='test.py',
                lineno=1,
                msg='Debug message',
                args=(),
                exc_info=None,
            )
            handler.handle(debug_record)

            # Handle INFO record (should pass) - use handle() not emit()
            info_record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Info message',
                args=(),
                exc_info=None,
            )
            handler.handle(info_record)
            handler.flush()

            # Check that only INFO message was logged
            with open(log_path) as f:
                content = f.read()
                assert 'Debug message' not in content
                assert 'Info message' in content

            handler.close()

    def test_level_applied_to_target(self):
        """Test that log level is respected when using through a logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_level.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
                level=logging.WARNING,
            )
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

            # Create a logger and add our handler
            logger = logging.getLogger('test_level_logger')
            logger.setLevel(logging.DEBUG)  # Logger accepts all levels
            logger.addHandler(handler)
            logger.propagate = False  # Don't propagate to root logger

            try:
                # Log INFO message (should be ignored by handler due to level)
                logger.info('Info message')

                # File should not be created because message was below handler's threshold
                assert not log_path.exists(), "File created for below-threshold message"

                # Log WARNING message (should be logged)
                logger.warning('Warning message')

                # Now file should exist with only WARNING message
                assert log_path.exists()
                handler.flush()
                with open(log_path) as f:
                    content = f.read()
                    assert 'Info message' not in content
                    assert 'WARNING: Warning message' in content

            finally:
                logger.removeHandler(handler)
                handler.close()

    def test_level_deferred_file_creation(self):
        """Test that file is not created when only below-threshold messages are logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_level_deferred.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
                level=logging.ERROR,  # Only ERROR and above
            )

            # Create a logger and add our handler
            logger = logging.getLogger('test_level_deferred_logger')
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.propagate = False

            try:
                # Try to log DEBUG, INFO, WARNING (all should be filtered by handler level)
                logger.debug('Debug message')
                logger.info('Info message')
                logger.warning('Warning message')

                # File should still not exist because all messages were filtered
                assert not log_path.exists(), "File should not be created when all messages are filtered"

            finally:
                logger.removeHandler(handler)
                handler.close()

    def test_handler_name_copied(self):
        """Test that handler name is copied to target handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_name.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
            )
            handler.name = 'my_test_handler'

            # Emit a record to trigger handler creation
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test',
                args=(),
                exc_info=None,
            )
            handler.emit(record)

            # Check that target handler has the same name
            assert handler._target_handler.name == 'my_test_handler'

            handler.close()

    def test_missing_target_class_raises_error(self):
        """Test that missing target_class raises an error."""
        handler = LazyHandler(filename='/tmp/test.log')

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None,
        )

        with pytest.raises(ValueError, match='target_class must be specified'):
            handler.emit(record)

    def test_invalid_target_class_raises_error(self):
        """Test that invalid target_class raises an error."""
        handler = LazyHandler(
            filename='/tmp/test.log',
            target_class='nonexistent.module.Handler',
        )

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None,
        )

        with pytest.raises(ValueError, match='Failed to import target handler class'):
            handler.emit(record)

    def test_close_without_emit(self):
        """Test that close() works even if no logs were ever emitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_close.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
            )

            # Close without emitting anything
            handler.close()

            # File should not exist
            assert not log_path.exists()

    def test_flush_without_emit(self):
        """Test that flush() works even if no logs were ever emitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_flush.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='logging.FileHandler',
                target_kwargs={'mode': 'w', 'encoding': 'utf-8'},
            )

            # Flush without emitting anything (should not raise error)
            handler.flush()

            # File should not exist
            assert not log_path.exists()

            handler.close()

    def test_compressed_timed_rotating_file_handler(self):
        """Test LazyHandler with CompressedTimedRotatingFileHandler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / 'test_compressed.log'

            handler = LazyHandler(
                filename=log_path,
                target_class='pfund_kit.logging.handlers.CompressedTimedRotatingFileHandler',
                target_kwargs={'when': 'S', 'interval': 5, 'backupCount': 2, 'utc': True},
            )

            # File should not exist yet
            assert not log_path.exists()

            # Emit a record
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg='Test message',
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            handler.flush()

            # File should now exist
            assert log_path.exists()

            handler.close()
