import datetime

from server.db.db import DB


def drop_all_data(db_instance: DB):
    """
    Deletes all entries from all tables in the database.

    :param db_instance: An instance of the DB class.
    """
    if not isinstance(db_instance, DB):
        raise ValueError("The provided object is not an instance of DB.")

    cursor = db_instance.cursor

    # Deleting data from tables
    cursor.execute("DELETE FROM inventory;")
    cursor.execute("DELETE FROM users;")

    # Commit the changes
    db_instance.conn.commit()
    print("All entries have been deleted from the database.")


def create_sample_data(db_instance: DB):
    """
    Adds sample data to the Customers, Vehicles, and Invoices tables in the database.

    :param db_instance: An instance of the DB class.
    """
    if not isinstance(db_instance, DB):
        raise ValueError("The provided object is not an instance of DB.")

    cursor = db_instance.cursor
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        users = [
            ('Hugo', 2, True, True),
            ('Jake', None, False, True),
            ('Adam', '53', True, True),
        ]
        user_ids = []
        for user in users:
            cursor.execute(
                'INSERT INTO users '
                '(name, barcode, is_admin, is_user) '
                'VALUES (?, ?, ?, ?) RETURNING id',
                user
            )
            user_id = cursor.fetchone()[0]
            user_ids.append(user_id)
        tools = [
            ('Jake', '2', 'Wow, what a tool', 'jake.png', True, user_ids[0], datetime.datetime.now(tz=datetime.timezone.utc)),
            ('Hammer', None, 'Hits stuff', None, True, user_ids[0], datetime.datetime.now(tz=datetime.timezone.utc)),
            ('Metric hex keys', '3', 'Metric lmao', None, True, user_ids[1], datetime.datetime.now(tz=datetime.timezone.utc)),
            ('Imperial hex keys', '5', 'Imperial lmao', None, True, user_ids[2], datetime.datetime.now(tz=datetime.timezone.utc)),
            ('Drill bits 1', None, 'Drill bits', None, False, None, None),
            ('Drill bits 2', 69, 'Drill bits', None, False, None, None),
        ]
        for tool in tools:
            cursor.execute(
                'INSERT INTO inventory (name, barcode, description, picture, signed_out, holder_id, signed_out_since) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                tool
            )


    # Commit the changes
    db_instance.conn.commit()
    print("Sample data created successfully.")


