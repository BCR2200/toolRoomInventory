import datetime
import logging
import os
import uuid

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, static_folder='app/public_static', static_url_path='/static')
app.template_folder = 'app/templates'


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
    if not get_user()['is_admin']:
        return redirect(url_for('dashboard'))

    return render_template('admin_dashboard.html.jinja2',
                           user=get_user(),
                           tools=get_inventory())


@app.route('/admin/add-tool', methods=['POST'])
def add_tool():
    if not get_user()['is_admin']:
        return redirect(url_for('dashboard'))

    name = request.form.get('name')
    description = request.form.get('description')

    # Generate a new unique ID
    new_id = max(_INVENTORY.keys()) + 1 if _INVENTORY else 1

    # Create new tool entry
    tool = {
        'name': name,
        'id': new_id,
        'description': description,
        'status': {
            'signed_out': False,
            'holder': None
        }
    }
    _INVENTORY[new_id] = tool

    # Handle picture upload if provided
    if 'picture' in request.files:
        save_tool_picture(new_id, tool)

    app.logger.info(f"New tool added: {name} (ID: {new_id})")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit-tool', methods=['POST'])
def edit_tool():
    if not get_user()['is_admin']:
        return redirect(url_for('dashboard'))

    tool_id = int(request.form.get('tool_id'))
    if tool_id not in _INVENTORY:
        return redirect(url_for('admin_dashboard'))

    tool = _INVENTORY[tool_id]
    tool['name'] = request.form.get('name')
    tool['description'] = request.form.get('description')

    # Handle picture upload if provided
    if 'picture' in request.files:
        save_tool_picture(tool_id, tool)

    app.logger.info(f"Tool updated: {tool['name']} (ID: {tool_id})")
    return redirect(url_for('admin_dashboard'))


def tool_image_filename(id):
    return f'img_tool_{id}_{uuid.uuid4().hex[:6]}'


def save_tool_picture(tool_id, tool):
    picture = request.files['picture']
    if picture.filename:
        filename = tool_image_filename(tool_id)
        os.makedirs(os.path.join(app.static_folder, 'tool_images'), exist_ok=True)
        picture.save(os.path.join(app.static_folder, 'tool_images', filename))
        old_picture = None
        if 'picture' in tool:
            old_picture = tool['picture']
        tool['picture'] = url_for('static', filename=f'tool_images/{filename}')
        if old_picture:
            try:
                os.remove(os.path.join(app.static_folder, 'tool_images', old_picture))
            except FileNotFoundError:
                pass


@app.route('/admin/delete-tool', methods=['POST'])
def delete_tool():
    if not get_user()['is_admin']:
        return redirect(url_for('dashboard'))

    tool_id = int(request.form.get('tool_id'))
    inventory = get_inventory()
    if tool_id in inventory:
        tool = inventory.pop(tool_id)
        if 'picture' in tool:
            try:
                os.remove(os.path.join(app.static_folder, 'tool_images', tool_image_filename(tool_id)))
            except FileNotFoundError:
                pass
        app.logger.info(f"Tool deleted: {tool['name']} (ID: {tool_id})")

    return redirect(url_for('admin_dashboard'))


@app.route('/borrow-tool', methods=['POST'])
def borrow_tool():
    tool_id = int(request.form.get('tool_id'))
    user_id = int(request.form.get('user_id'))
    inventory = get_inventory()
    if tool_id in inventory and not inventory[tool_id]['status']['signed_out']:
        inventory[tool_id]['status']['signed_out'] = True
        inventory[tool_id]['status']['holder'] = {
            'id': user_id,
            'since': datetime.datetime.now().isoformat()
        }
        app.logger.info(f"Tool {tool_id} has been borrowed by user {user_id}.")
    else:
        app.logger.warning(f"Attempt to borrow unavailable tool {tool_id}.")
    return redirect(url_for('dashboard'))


@app.route('/return-tool', methods=['POST'])
def return_tool():
    tool_id = int(request.form.get('tool_id'))
    user_id = int(request.form.get('user_id'))
    inventory = get_inventory()
    if tool_id in inventory and inventory[tool_id]['status']['signed_out']:
        inventory[tool_id]['status']['signed_out'] = False
        inventory[tool_id]['status']['holder'] = None
        app.logger.info(f"Tool {tool_id} has been borrowed by user {user_id}.")
    else:
        app.logger.warning(f"Attempt to return non-signed-out tool {tool_id}.")
    return redirect(url_for('dashboard'))


_USERS = {
    24: {
        'id': 24,
        'name': 'Hugo',
        'is_admin': True,
        'is_user': True,
    }
}


def get_users():
    return _USERS


def get_user():
    return _USERS[24]


_INVENTORY = {
    42: {
        'name': 'hammer',
        'id': 42,
        'description': 'hits stuff',
        'status': {
            'signed_out': False,
            'holder': None
        }
    },
    43: {
        'name': 'ethernet cable',
        'id': 43,
        'description': '6ft cat5',
        'status': {
            'signed_out': True,
            'holder': {
                'id': 24,
                'since': '2025-03-22T14:52:37.659071+00:00'
            }
        }
    },
    1: {
        'name': 'Jake',
        'id': 1,
        'description': 'hits stuff',
        'picture': '/static/tool_images/jake.png',
        'status': {
            'signed_out': True,
            'holder': {
                'id': 24,
                'since': '2025-03-22T14:52:37.659071+00:00'
            }
        }
    }
}


def get_inventory():
    return _INVENTORY


def get_available_tools():
    return {id: tool for id, tool in get_inventory().items() if not tool['status']['signed_out']}


def get_signed_out_tools():
    return {id: tool for id, tool in get_inventory().items() if tool['status']['signed_out']}


def get_my_tools():
    return {
        id: tool
        for id, tool in get_signed_out_tools().items()
        if tool['status']['signed_out'] and tool['status']['holder']['id'] == get_user()['id']
    }


def main():
    app.logger.level = logging.INFO
    app.run(host='127.0.0.1', port=5000, debug=True)

if __name__ == "__main__":
    main()