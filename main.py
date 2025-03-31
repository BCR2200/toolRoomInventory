import datetime
import json
import logging
from pathlib import Path
from typing import Dict

from flask import Flask, render_template, request, redirect, url_for, g, send_from_directory
from server.db.db import DB
from server.db.helpers import create_sample_data, drop_all_data
from server.qr import generate_qr_code
from server.tool import Tool
from server.user import User

app = Flask(__name__, static_folder='app/public_static', static_url_path='/static')
app.template_folder = 'app/templates'

DATA_PATH = Path('data')
DB_PATH = DATA_PATH / 'inventory.db'
TOOL_IMAGES_PATH = DATA_PATH / 'tool_images'
TOOL_IMAGES_PATH.mkdir(exist_ok=True)
TOOL_BARCODES_PATH = DATA_PATH / 'tool_barcodes'
TOOL_BARCODES_PATH.mkdir(exist_ok=True)


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


@app.route('/tool-image/<path:img>')
def tool_image(img):
    ensure_path_in_base(TOOL_IMAGES_PATH, TOOL_IMAGES_PATH / img)
    return send_from_directory(TOOL_IMAGES_PATH, img)


@app.route('/tool-barcode/<path:img>')
def tool_barcode(img):
    ensure_path_in_base(TOOL_BARCODES_PATH, TOOL_BARCODES_PATH / img)
    return send_from_directory(TOOL_BARCODES_PATH, img)

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


@app.route('/tool/<tool_id>')
def tool_detail(tool_id):
    user = get_user()
    tool = get_inventory().get(int(tool_id))
    if tool is None:
        return redirect(url_for('dashboard', result=json.dumps({
            'success': False,
            'message': f"Tool with ID {tool_id} does not exist."
        })))
    return render_template('tool_detail.html.jinja2', tool=tool, user=user, users=get_users())


@app.route('/admin/add-tool', methods=['POST'])
def add_tool():
    if not get_user().is_admin:
        return redirect(url_for('dashboard', result=json.dumps({
            'success': False,
            'message': 'You do not have permission to access this page.'
        })))

    name = request.form.get('name')
    description = request.form.get('description')
    allocate_barcode = request.form.get('allocate_barcode')
    barcode = request.form.get('barcode') or None
    picture_path = None
    # Handle picture upload if provided
    if 'picture' in request.files:
        pic = request.files['picture']
        if pic.filename != '':
            picture_path = save_tool_picture().as_posix()

    # Start exclusive transaction so that we know we allocate a unique barcode
    g.db.cursor.execute('BEGIN EXCLUSIVE TRANSACTION')
    try:
        if allocate_barcode:
            # Select the lowest open ID in the range [1, inf)
            g.db.cursor.execute('''
                SELECT MIN(t1.barcode + 1)
                FROM inventory AS t1
                LEFT JOIN inventory AS t2 ON t1.barcode + 1 = t2.barcode
                WHERE t2.barcode IS NULL
            ''')
            barcode = g.db.cursor.fetchone()[0] or 1
            # Generate and save QR code image
            qr_filename = f"qr_{barcode}.png"
            qr_path = Path(TOOL_IMAGES_PATH) / qr_filename
            ensure_path_in_base(TOOL_IMAGES_PATH, qr_path)
            ensure_barcode(barcode)
            app.logger.debug(
                f"Generating QR code for barcode {barcode} and saving to {qr_path}"
            )
        elif barcode:
            # Make sure the barcode is not already allocated
            g.db.cursor.execute('SELECT name FROM inventory WHERE barcode = ?', (barcode,))
            results = g.db.cursor.fetchall()
            if len(results) > 0:
                other = results[0]
                e_msg = f'Error adding tool: barcode already in use by: {other[0]}'
                app.logger.error(e_msg)
                return redirect(url_for('admin_dashboard', result=json.dumps({
                    'success': False,
                    'message': e_msg
                })))
            ensure_barcode(barcode)
        tool = Tool(tool_id=None, name=name, barcode=barcode, description=description, picture=picture_path,
                    signed_out=False, holder_id=None, signed_out_since=None)
        row, projection = tool.to_row_and_projection()

        # Insert new tool
        g.db.cursor.execute(f'''
            INSERT INTO inventory {projection[0]}
            VALUES {projection[1]}
            RETURNING id
        ''', row)
        new_id = g.db.cursor.fetchone()[0]
        g.db.conn.commit()
        app.logger.info(f"New tool added: {name} (ID: {new_id})")
        return redirect(url_for('admin_dashboard', result=json.dumps({
            'success': True,
            'message': f"Tool '{name}' added successfully."
        })))
    except Exception as e:
        g.db.conn.rollback()
        e_msg = f'Error adding tool: {e}'
        app.logger.error(e_msg)
        return redirect(url_for('admin_dashboard', result=json.dumps({
            'success': False,
            'message': e_msg
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
    allocate_barcode = request.form.get('allocate_barcode')
    barcode = request.form.get('barcode') or None
    # Handle picture upload if provided
    if 'picture' in request.files:
        pic = request.files['picture']
        if pic.filename != '':
            picture_path = save_tool_picture().as_posix()

    # Start transaction with SERIALIZABLE isolation
    g.db.cursor.execute('BEGIN IMMEDIATE TRANSACTION')
    old_picture_path = None
    try:
        if allocate_barcode:
            # Select the lowest open ID in the range [1, inf)
            g.db.cursor.execute('''
                SELECT MIN(t1.barcode + 1)
                FROM inventory AS t1
                LEFT JOIN inventory AS t2 ON t1.barcode + 1 = t2.barcode
                WHERE t2.barcode IS NULL
            ''')
            barcode = g.db.cursor.fetchone()[0] or 1
            # Generate and save QR code image
            qr_filename = f"qr_{barcode}.png"
            qr_path = Path(TOOL_IMAGES_PATH) / qr_filename
            ensure_path_in_base(TOOL_IMAGES_PATH, qr_path)
            ensure_barcode(barcode)
            app.logger.debug(
                f"Generating QR code for barcode {barcode} and saving to {qr_path}"
            )
        elif barcode:
            # Make sure the barcode is not already allocated
            g.db.cursor.execute('SELECT name FROM inventory WHERE barcode = ?', (barcode,))
            results = g.db.cursor.fetchall()
            if len(results) > 0:
                other = results[0]
                e_msg = f'Error adding tool: barcode already in use by: {other[0]}'
                app.logger.error(e_msg)
                return redirect(url_for('admin_dashboard', result=json.dumps({
                    'success': False,
                    'message': e_msg
                })))
            ensure_barcode(barcode)
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
        sanitized_old_path = ensure_path_in_base(TOOL_IMAGES_PATH, TOOL_IMAGES_PATH / Path(old_picture_path))
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
        g.db.cursor.execute('DELETE FROM inventory WHERE id = ? RETURNING name, picture', (tool_id,))
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
        sanitized_old_path = ensure_path_in_base(TOOL_IMAGES_PATH, TOOL_IMAGES_PATH / Path(old_picture_path))
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
    g.db.cursor.execute(f'SELECT {', '.join(User.default_projection())} FROM users')
    return {
        row[0]: User.from_row(row)
        for row in g.db.cursor.fetchall()
    }

def get_user() -> User:
    # TODO: get the user from the request
    return User.from_row(
        g.db.cursor.execute(f"SELECT {', '.join(User.default_projection())} from users where name = 'Hugo'").fetchone()
    )

def get_inventory() -> Dict[int, Tool]:
    g.db.cursor.execute(f'''
        SELECT {', '.join(Tool.default_projection())} 
        FROM inventory
    ''')
    return {
        row[0]: Tool.from_row(row)
        for row in g.db.cursor.fetchall()
    }

def get_available_tools() -> Dict[int, Tool]:
    return {tool_id: tool for tool_id, tool in get_inventory().items() if not tool.signed_out}


def get_signed_out_tools() -> Dict[int, Tool]:
    return {tool_id: tool for tool_id, tool in get_inventory().items() if tool.signed_out}


def get_my_tools() -> Dict[int, Tool]:
    return {
        tool_id: tool
        for tool_id, tool in get_signed_out_tools().items()
        if tool.signed_out and tool.holder_id == get_user().user_id
    }


def save_tool_picture():
    if 'picture' not in request.files:
        return None
    picture = request.files['picture']
    if picture.filename:
        filename = picture.filename
        final_path = sanitize_path(TOOL_IMAGES_PATH, filename)
        picture.save(final_path)
        return final_path.relative_to(TOOL_IMAGES_PATH)


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


def ensure_all_have_barcode(db: DB):
    # Find all tools with a barcode
    db.cursor.execute('''
        SELECT barcode
        FROM inventory 
        WHERE barcode IS NOT NULL
    ''')
    tools_with_barcodes = db.cursor.fetchall()

    for (barcode,) in tools_with_barcodes:
        ensure_barcode(barcode)


def ensure_barcode(barcode: str):
    img_path = Path(TOOL_BARCODES_PATH) / f"qr_{barcode}.png"
    if not img_path.exists():
        generate_qr_code(str(barcode), img_path)


def main():
    app.logger.level = logging.DEBUG

    # Initialize database
    DB_PATH.parent.mkdir(exist_ok=True)
    # Initialize default users if they don't exist
    with DB(DB_PATH, auto_migrate=True) as db:
        db.self_test()
        drop_all_data(db)
        create_sample_data(db)
        ensure_all_have_barcode(db)

    app.run(host='::1', port=5000, debug=True)

if __name__ == "__main__":
    main()