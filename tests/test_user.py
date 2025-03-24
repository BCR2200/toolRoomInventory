import unittest

from server.db.db import DB
from server.user import User


class TestUser(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:", auto_migrate=True)
        self.db.connect()

    def tearDown(self):
        self.db.close()

    def test_from_row_with_valid_data(self):
        values = [
            (1, 'Alice', True, False),
            (2, 'Bob', False, True),
            (3, 'Charlie', False, False),
            (4, 'David', True, True),
        ]
        for value in values:
            # Insert a valid user record
            self.db.cursor.execute("INSERT INTO users (id, name, is_admin, is_user) VALUES (?, ?, ?, ?)",
                                   value)
        self.db.conn.commit()
        for user_id, name, is_admin, is_user in values:
            # Retrieve the inserted record
            self.db.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = self.db.cursor.fetchone()
            # Use from_row on the retrieved data
            user = User.from_row(row)
            self.assertEqual(user_id, user.user_id)
            self.assertEqual(name, user.name)
            self.assertEqual(is_admin, user.is_admin)
            self.assertEqual(is_user, user.is_user)

    def test_from_row_with_invalid_data_type(self):
        self.db.cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (1, "Bob", 1, 0))
        self.db.conn.commit()
        self.db.cursor.execute("SELECT 'invalid' as id, name, is_admin, is_user FROM users WHERE name = ?", ("Bob",))
        row = self.db.cursor.fetchone()
        # Test that from_row raises ValueError
        with self.assertRaises(ValueError):
            User.from_row(row)

    def test_from_row_with_missing_fields(self):
        # Insert a row with missing fields
        self.db.cursor.execute("INSERT INTO users (id, name, is_admin) VALUES (?, ?, ?)", (2, "Charlie", 1))
        self.db.conn.commit()
        self.db.cursor.execute("SELECT id, name, is_admin FROM users WHERE id = ?", (2,))
        row = self.db.cursor.fetchone()
        # Test that from_row raises IndexError
        with self.assertRaises(IndexError):
            User.from_row(row)

    def test_from_row_with_empty_row(self):
        # Insert no rows into the table
        row = None  # Simulate an empty row
        # Test that from_row raises TypeError when row is None
        with self.assertRaises(ValueError):
            User.from_row(row)

    def test_from_row_with_extra_fields(self):
        # Insert a row with extra fields
        self.db.cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (3, "Dana", 0, 1))
        self.db.conn.commit()
        self.db.cursor.execute("SELECT *, 'extra_field' as foo FROM users WHERE id = ?", (3,))
        row = self.db.cursor.fetchone()
        # Verify from_row works with just the required fields
        user = User.from_row(row)
        self.assertEqual(3, user.user_id)
        self.assertEqual("Dana", user.name)
        self.assertEqual(False, user.is_admin)
        self.assertEqual(True, user.is_user)


if __name__ == "__main__":
    unittest.main()
