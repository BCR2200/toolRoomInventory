import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Dict

from flask import Flask, render_template, request, redirect, url_for, g
from server.db.db import DB
from server.db.helpers import create_sample_data, drop_all_data
from server.user import User

app = Flask(__name__, static_folder='app/public_static', static_url_path='/static')
app.template_folder = 'app/templates'


TOOL_IMAGES_PATH = Path(app.static_folder) / 'tool_images'
TOOL_IMAGES_PATH.mkdir(exist_ok=True)


@app.before_request
def set_request_globals():
    """Set up a new database connection for each request."""
    g.db = DB(DB_PATH)
    g.db.connect()
    # TODO
    # g.user = webserver.authnz.authorize.logged_in_user()
    # g.user_role = webserver.authnz.authorize.logged_in_user_role()


@app.after_request
def cleanup(response):
    """Clean up the database connection after each request."""
    if hasattr(g, 'db'):
        g.db.close()
    return response


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'))


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html.jinja2',
                           user=get_user(),
                           users=get_users(),
                           my_tools=get_my_tools(),
                           available_tools=get_available_tools(),
                           signed_out_tools=get_signed_out_tools())


# Update the admin_dashboard route
@app.route('/admin-dashboard')
def admin_dashboard():
    if not get_user().is_admin:
        return redirect(url_for('dashboard', result=json.dumps({
            'success': False,
            'message': 'You do not have permission to access this page.'
        })))

    return render_template('admin_dashboard.html.jinja2',
                           user=get_user(),
                           tools=get_inventory())


@app.route('/admin/add-tool', methods=['POST'])
def add_tool():
    if not get_user().is_admin:
        return redirect(url_for('dashboard', result=json.dumps({
            'success': False,
            'message': 'You do not have permission to access this page.'
        })))

    name = request.form.get('name')
    description = request.form.get('description')
    picture_path = None
    # Handle picture upload if provided
    if 'picture' in request.files:
        picture_path = save_tool_picture()

    # Insert new tool
    g.db.cursor.execute('''
        INSERT INTO inventory (name, description, picture, signed_out, holder_id, signed_out_since)
        VALUES (?, ?, ?, 0, NULL, NULL)
        RETURNING id
    ''', (name, description, picture_path))
    new_id = g.db.cursor.fetchone()[0]
    g.db.conn.commit()

    app.logger.info(f"New tool added: {name} (ID: {new_id})")
    return redirect(url_for('admin_dashboard', result=json.dumps({
        'success': True,
        'message': f"Tool '{name}' added successfully."
    })))


@app.route('/admin/edit-tool', methods=['POST'])
def edit_tool():
    if not get_user().is_admin:
        return redirect(url_for('dashboard', result=json.dumps({
            'success': False,
            'message': 'You do not have permission to access this page.'
        })))

    tool_id = int(request.form.get('tool_id'))
    name = request.form.get('name')
    description = request.form.get('description')
    picture_path = None
    # Handle picture upload if provided
    if 'picture' in request.files:
        picture_path = save_tool_picture()

    # Start transaction with SERIALIZABLE isolation
    g.db.cursor.execute('BEGIN IMMEDIATE TRANSACTION')
    old_picture_path = None
    try:
        # Get the current picture value
        g.db.cursor.execute('SELECT picture FROM inventory WHERE id = ?', (tool_id,))
        old_picture_path = g.db.cursor.fetchone()[0]

        # Update tool
        g.db.cursor.execute('''
            UPDATE inventory 
            SET name = ?, description = ?, picture = COALESCE(?, picture)
            WHERE id = ?
        ''', (name, description, picture_path, tool_id))

        g.db.conn.commit()
    except Exception as e:
        g.db.conn.rollback()
        e_msg = f'Error updating tool: {e}'
        app.logger.error(e_msg)
        return redirect(url_for('admin_dashboard', result=json.dumps({
            'success': False,
            'message': e_msg
        })))
    if old_picture_path:
        # Clean up old picture
        sanitized_old_path = ensure_path_in_base(TOOL_IMAGES_PATH, old_picture_path)
        sanitized_old_path.unlink()
        app.logger.debug(f"Old picture deleted (ID: {tool_id}): {sanitized_old_path}")
    app.logger.info(f"Tool updated: {name} (ID: {tool_id})")
    return redirect(url_for('admin_dashboard', result=json.dumps({
        'success': True,
        'message': f"Tool '{name}' updated successfully."
    })))


@app.route('/admin/delete-tool', methods=['POST'])
def delete_tool():
    if not get_user().is_admin:
        return redirect(url_for('dashboard', result=json.dumps({
            'success': False,
            'message': 'You do not have permission to access this page.'
        })))

    tool_id = int(request.form.get('tool_id'))

    g.db.cursor.execute('BEGIN IMMEDIATE TRANSACTION')
    old_picture_path = None
    try:
        g.db.cursor.execute('DELETE FROM main.inventory WHERE id = ? RETURNING name, picture', (tool_id,))
        tool, old_picture_path = g.db.cursor.fetchone()
    except Exception as e:
        g.db.conn.rollback()
        e_msg = f'Error deleting tool: {e}'
        app.logger.error(e_msg)
        return redirect(url_for('admin_dashboard', result=json.dumps({
            'success': False,
            'message': e_msg
        })))
    if old_picture_path:
        # Clean up old picture
        sanitized_old_path = ensure_path_in_base(TOOL_IMAGES_PATH, old_picture_path)
        sanitized_old_path.unlink()
        app.logger.debug(f"Old picture deleted (ID: {tool_id}): {sanitized_old_path}")
    app.logger.info(f"Tool deleted: {tool} (ID: {tool_id})")
    return redirect(url_for('admin_dashboard', result=json.dumps({
        'success': True,
        'message': f"Tool '{tool}' deleted successfully."
    })))


@app.route('/borrow-tool', methods=['POST'])
def borrow_tool():
    tool_id = int(request.form.get('tool_id'))
    # TODO: get user from user making request, not user that the user said is making the request
    user_id = int(request.form.get('user_id'))

    # Check if tool exists and is available
    g.db.cursor.execute('''
        SELECT signed_out FROM inventory 
        WHERE id = ? AND signed_out = 0
    ''', (tool_id,))
    if g.db.cursor.fetchone():
        # Update tool status
        g.db.cursor.execute('''
            UPDATE inventory 
            SET signed_out = 1, 
                holder_id = ?,
                signed_out_since = ?
            WHERE id = ?
        ''', (user_id, datetime.datetime.now().isoformat(), tool_id))
        g.db.conn.commit()
        app.logger.info(f"Tool {tool_id} has been borrowed by user {user_id}.")
    else:
        app.logger.warning(f"Attempt to borrow unavailable tool {tool_id}.")

    return redirect(url_for('dashboard'))


@app.route('/return-tool', methods=['POST'])
def return_tool():
    tool_id = int(request.form.get('tool_id'))
    user_id = int(request.form.get('user_id'))

    # Check if tool exists and is signed out
    g.db.cursor.execute('''
        SELECT signed_out FROM inventory 
        WHERE id = ? AND signed_out = 1
    ''', (tool_id,))
    if g.db.cursor.fetchone():
        # Update tool status
        g.db.cursor.execute('''
            UPDATE inventory 
            SET signed_out = 0,
                holder_id = NULL,
                signed_out_since = NULL
            WHERE id = ?
        ''', (tool_id,))
        g.db.conn.commit()
        app.logger.info(f"Tool {tool_id} has been returned by user {user_id}.")
    else:
        app.logger.warning(f"Attempt to return non-signed-out tool {tool_id}.")

    return redirect(url_for('dashboard'))


def get_users() -> Dict[int, User]:
    g.db.cursor.execute('SELECT id, name, is_admin, is_user FROM users')
    return {
        row[0]: User.from_row(row)
        for row in g.db.cursor.fetchall()
    }

def get_user() -> User:
    # TODO: get the user from the request
    return User.from_row(
        g.db.cursor.execute(f"SELECT {', '.join(User.default_projection())} from users where name = 'Hugo'").fetchone()
    )

def get_inventory():
    g.db.cursor.execute('''
        SELECT id, name, description, picture, signed_out, holder_id, signed_out_since 
        FROM inventory
    ''')
    return {
        row[0]: {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'picture': row[3],
            'status': {
                'signed_out': bool(row[4]),
                'holder': {
                    'id': row[5],
                    'since': row[6]
                } if row[5] is not None else None
            }
        }
        for row in g.db.cursor.fetchall()
    }

def get_available_tools():
    return {tool_id: tool for tool_id, tool in get_inventory().items() if not tool['status']['signed_out']}


def get_signed_out_tools():
    return {tool_id: tool for tool_id, tool in get_inventory().items() if tool['status']['signed_out']}


def get_my_tools():
    return {
        tool_id: tool
        for tool_id, tool in get_signed_out_tools().items()
        if tool['status']['signed_out'] and tool['status']['holder']['id'] == get_user().user_id
    }


def save_tool_picture():
    if 'picture' not in request.files:
        return None
    picture = request.files['picture']
    if picture.filename:
        filename = uuid.uuid4().hex
        final_path = sanitize_path(TOOL_IMAGES_PATH, filename)
        picture.save(final_path)
        return final_path


def sanitize_path(base_path, path, allow_subdirs:bool = False):
    new_path = Path(base_path) / path
    new_path = ensure_path_in_base(base_path, new_path, allow_subdirs=allow_subdirs)
    return new_path.resolve()


def ensure_path_in_base(base_path, path, allow_subdirs:bool = False):
    '''Ensure that the path is within the base directory and does not contain parent directory references.'''
    base_path = Path(base_path).resolve()
    test_path = Path(path).resolve()
    if allow_subdirs:
        if not base_path in test_path.parents:
            raise ValueError("Invalid path")
    else:
        if base_path != test_path.parent:
            raise ValueError("Invalid path")
    return test_path


DB_PATH = Path('data/inventory.db')


def main():
    app.logger.level = logging.DEBUG

    # Initialize database
    DB_PATH.parent.mkdir(exist_ok=True)
    # Initialize default users if they don't exist
    with DB(DB_PATH, auto_migrate=True) as db:
        db.self_test()
        drop_all_data(db)
        create_sample_data(db)

    app.run(host='127.0.0.1', port=5000, debug=True)

if __name__ == "__main__":
    main()