import datetime
import unittest
from pathlib import Path

from server.db.db import DB
from server.tool import Tool


class TestTool(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:", auto_migrate=True)
        self.db.connect()

    def tearDown(self):
        self.db.close()

    def test_from_row_with_valid_data(self):
        self.db.cursor.execute('INSERT INTO users (id, name, is_admin, is_user) VALUES (?, ?, ?, ?)', (1, 'Alice', True, False))
        values = [
            (1, 'hammer', 'hits stuff', None, False, None, None),
            (2, 'Jake', 'lmao', 'jake.png', True, 1, datetime.datetime.now(tz=datetime.timezone.utc)),
        ]
        for tool_id, name, description, picture, signed_out, holder_id, signed_out_since in values:
            # Insert a valid tool record
            self.db.cursor.execute('''
            INSERT INTO inventory 
            (id, name, description, picture, signed_out, holder_id, signed_out_since) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (tool_id, name, description, picture, signed_out, holder_id, signed_out_since.isoformat() if signed_out_since else None) )
        self.db.conn.commit()
        for tool_id, name, description, picture, signed_out, holder_id, signed_out_since in values:
            # Retrieve the inserted record
            self.db.cursor.execute("SELECT * FROM inventory WHERE id = ?", (tool_id,))
            row = self.db.cursor.fetchone()
            # Use from_row on the retrieved data
            tool = Tool.from_row(row)
            self.assertEqual(tool_id, tool.tool_id)
            self.assertEqual(name, tool.name)
            self.assertEqual(description, tool.description)
            if picture:
                picture = Path(picture)
            self.assertEqual(picture, tool.picture)
            self.assertEqual(signed_out, tool.signed_out)
            self.assertEqual(holder_id, tool.holder_id)
            self.assertEqual(signed_out_since, tool.signed_out_since)

    def test_from_row_with_invalid_data_type(self):
        self.db.cursor.execute('INSERT INTO inventory (id, name, description, signed_out) VALUES (?, ?, ?, ?)',
                               (1, "Drill", "A powerful handheld drill", False))
        self.db.conn.commit()
        self.db.cursor.execute("SELECT 'invalid' as id, name, description, picture, signed_out, holder_id, signed_out_since FROM inventory WHERE name = ?", ("Drill",))
        row = self.db.cursor.fetchone()
        # Test that from_row raises ValueError
        with self.assertRaises(ValueError):
            Tool.from_row(row)

    def test_from_row_with_missing_fields(self):
        # Insert a row with missing fields
        self.db.cursor.execute("INSERT INTO inventory (id, name) VALUES (?, ?)", (1, "Hammer"))
        self.db.conn.commit()
        self.db.cursor.execute("SELECT id, name FROM inventory WHERE id = ?", (1,))
        row = self.db.cursor.fetchone()
        # Test that from_row raises IndexError
        with self.assertRaises(IndexError):
            Tool.from_row(row)

    def test_from_row_with_empty_row(self):
        # Insert no rows into the table
        row = None  # Simulate an empty row
        # Test that from_row raises TypeError when row is None
        with self.assertRaises(ValueError):
            Tool.from_row(row)

    def test_from_row_with_extra_fields(self):
        # Insert a row with extra fields
        self.db.cursor.execute("INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (5, "Wrench", "A sturdy wrench", "wrench.png", False, None, None))
        self.db.conn.commit()
        self.db.cursor.execute("SELECT *, 'extra_field' as foo FROM inventory WHERE id = ?", (5,))
        row = self.db.cursor.fetchone()
        # Verify from_row works with just the required fields
        tool = Tool.from_row(row)
        self.assertEqual(5, tool.tool_id)
        self.assertEqual("Wrench", tool.name)
        self.assertEqual("A sturdy wrench", tool.description)
        self.assertEqual(Path("wrench.png"), tool.picture)
        self.assertEqual(False, tool.signed_out)
        self.assertIsNone(tool.holder_id)
        self.assertIsNone(tool.signed_out_since)


if __name__ == "__main__":
    unittest.main()
