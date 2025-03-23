from server.db.db import DB


def drop_all_data(db_instance: DB):
    """
    Deletes all entries from all tables in the database. TODO

    :param db_instance: An instance of the DB class.
    """
    if not isinstance(db_instance, DB):
        raise ValueError("The provided object is not an instance of DB.")

    cursor = db_instance.cursor

    # Deleting data from tables TODO

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

    # TODO actually have real sample data to serve

    # Commit the changes
    db_instance.conn.commit()
    print("Sample data created successfully.")


