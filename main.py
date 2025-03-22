import datetime
import logging

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, static_folder='app/public_static', static_url_path='/static')
app.template_folder = 'app/templates'


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html.jinja2',
                           user=get_user(),
                           users=get_users(),
                           my_tools=get_my_tools(),
                           available_tools=get_available_tools(),
                           signed_out_tools=get_signed_out_tools())


@app.route('/admin-dashboard')
def admin_dashboard():
    # TODO make admin dashboard
    return render_template('dashboard.html.jinja2',
                           user=get_user(),
                           users=get_users(),
                           tools=get_inventory())


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