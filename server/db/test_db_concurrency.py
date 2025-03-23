import os
import threading
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from server.db.db import DB


class TestDBConcurrency(unittest.TestCase):
    def setUp(self):
        """Create a temporary database file and initialize it with schema."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        # Initialize DB with migrations
        with DB(self.db_path, auto_migrate=True) as db:
            # Create test counter table
            db.cursor.execute('''
            CREATE TABLE counter (
                id INTEGER PRIMARY KEY,
                value INTEGER NOT NULL
            )
            ''')
            db.cursor.execute('INSERT INTO counter (id, value) VALUES (1, 0)')
            db.conn.commit()
    
    def tearDown(self):
        """Clean up temporary files."""
        try:
            os.remove(self.db_path)
            os.remove(self.db_path + "-wal")  # Remove WAL file
            os.remove(self.db_path + "-shm")  # Remove shared memory file
        except FileNotFoundError:
            pass
        os.rmdir(self.temp_dir)

    def test_concurrent_reads(self):
        """Test that multiple threads can read from the database simultaneously."""
        NUM_THREADS = 10
        READS_PER_THREAD = 50
        results = []
        errors = []

        def read_counter():
            try:
                with DB(self.db_path) as db:
                    db.cursor.execute("SELECT value FROM counter WHERE id = 1")
                    return db.cursor.fetchone()[0]
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = [executor.submit(read_counter) for _ in range(NUM_THREADS * READS_PER_THREAD)]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(errors), 0, f"Encountered errors during concurrent reads: {errors}")
        self.assertTrue(all(r is not None for r in results), "Some reads returned None")
        self.assertTrue(all(r == results[0] for r in results), "Inconsistent read results")

    def test_concurrent_writes(self):
        """Test that multiple threads can write to the database without errors."""
        NUM_THREADS = 5
        WRITES_PER_THREAD = 20
        errors = []

        def increment_counter():
            try:
                with DB(self.db_path) as db:
                    db.cursor.execute("UPDATE counter SET value = value + 1 WHERE id = 1")
                    return True
            except Exception as e:
                errors.append(e)
                return None

        # Run concurrent writes
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = [
                executor.submit(increment_counter) 
                for _ in range(NUM_THREADS * WRITES_PER_THREAD)
            ]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(errors), 0, f"Encountered errors during concurrent writes: {errors}")
        self.assertTrue(all(r is not None for r in results), "Some writes failed")

        # Verify final counter value
        with DB(self.db_path) as db:
            db.cursor.execute("SELECT value FROM counter WHERE id = 1")
            final_value = db.cursor.fetchone()[0]
            self.assertEqual(
                final_value, 
                NUM_THREADS * WRITES_PER_THREAD,
                f"Expected {NUM_THREADS * WRITES_PER_THREAD} increments, but got {final_value}"
            )

    def test_concurrent_reads_during_writes(self):
        """Test that reads can occur while writes are happening."""
        NUM_READERS = 8
        NUM_WRITERS = 4
        OPERATIONS_PER_THREAD = 25
        errors: List[Exception] = []
        read_results: List[dict] = []
        read_lock = threading.Lock()

        def read_counter():
            try:
                with DB(self.db_path) as db:
                    db.cursor.execute("SELECT value FROM counter WHERE id = 1")
                    value = db.cursor.fetchone()[0]
                    with read_lock:
                        read_results.append({
                            'timestamp': time.time(),
                            'value': value
                        })
                    return value
            except Exception as e:
                errors.append(e)
                return None

        def increment_counter():
            try:
                with DB(self.db_path) as db:
                    # Small delay to increase chance of interleaving
                    time.sleep(0.001)
                    db.cursor.execute("UPDATE counter SET value = value + 1 WHERE id = 1")
                    return True
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=NUM_READERS + NUM_WRITERS) as executor:
            # Submit both reads and writes simultaneously
            futures = (
                [executor.submit(increment_counter) for _ in range(NUM_WRITERS * OPERATIONS_PER_THREAD)] +
                [executor.submit(read_counter) for _ in range(NUM_READERS * OPERATIONS_PER_THREAD)]
            )
            all_results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(errors), 0, f"Encountered errors during concurrent operations: {errors}")
        self.assertTrue(all(r is not None for r in all_results), "Some operations failed")
        
        # Sort read results by timestamp
        sorted_reads = sorted(read_results, key=lambda x: x['timestamp'])
        
        # Verify that we see increasing values in at least some reads
        values_seen = set(r['value'] for r in sorted_reads)
        self.assertGreater(
            len(values_seen), 1,
            "Expected to see multiple different counter values during concurrent operations"
        )
        
        # Verify final counter value
        with DB(self.db_path) as db:
            db.cursor.execute("SELECT value FROM counter WHERE id = 1")
            final_value = db.cursor.fetchone()[0]
            self.assertEqual(
                final_value,
                NUM_WRITERS * OPERATIONS_PER_THREAD,
                f"Expected {NUM_WRITERS * OPERATIONS_PER_THREAD} increments, but got {final_value}"
            )
        
        # Print debug information
        print(f"\nCounter progression:")
        print(f"Initial value: {sorted_reads[0]['value']}")
        print(f"Final value: {sorted_reads[-1]['value']}")
        print(f"Total reads recorded: {len(sorted_reads)}")
        print(f"Number of different values seen: {len(values_seen)}")
        print(f"Values seen: {sorted(values_seen)}")


if __name__ == '__main__':
    unittest.main() 