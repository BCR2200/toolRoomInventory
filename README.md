# Tool Room Inventory (TRI)

A software solution for managing the inventory and sign-out process for tools 
in a machine shop. This system helps Burlington Community Robotics (BCR) track 
tools, manage borrowing, and maintain inventory efficiently.

## Features

- Tool management system with details including names, pictures, IDs, and descriptions
- User authentication via BCR ID cards
- Tool borrowing functionality for team members
- Administrative tools for managing inventory
- Dashboards showing:
  - Signed-out tools
  - Available tools for borrowing

## User Roles

- **Team Members**: Can borrow tools and view tool dashboards
- **Administrators**: Can manage tool inventory (add/remove/edit) and users

## Setup Instructions

1. Create and activate the virtual environment by running:
   ```bash
   source setup.bash
   ```
   This will set up a Python virtual environment and install all required dependencies.

2. Run the application:
   ```bash
   python main.py
   ```
   
## Running Tests

To run all Python tests for the project, ensure you have activated the virtual environment first, then use:

```bash
python -m unittest discover
```

## Requirements
- Python>=3.13

## Notes
- Make sure you have Python installed on your system before running the setup script
- The setup script (`setup.bash`) will create a virtual environment and install all necessary dependencies
- Run all commands from the root directory of the project