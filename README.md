# AsanaOps
AsanaOps is a Python utility for exploring Asana workspaces, portfolios, projects, sections, and tasks, with support for bulk task creation from Excel spreadsheets.

# Features
- List available Asana workspaces
- List portfolios within a workspace
- List projects
- List project sections
- List tasks within a project
- Bulk create tasks from an Excel file

# Requirements
Python 3.10+
Asana Personal Access Token (PAT)

# Installation
```sh
git clone https://github.com/your-org/asanaops.git
cd asanaops
pip install -r requirements.txt
```

# Configuration
Create an .env file:
```txt
ASANA_TOKEN=your_personal_access_token
#WORKSPACE_ID=xxxxx
#PROJECT_ID=xxxx
#SECTION_ID=xxxxx
```

# Capabilities
The script supports creating tasks in bulk from an Excel spreadsheet. 
