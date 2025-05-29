# Timesheet MCP Server

An MCP (Model Code Processing) server for logging time to the Insider system.

## Features

- List all projects available to the user
- Log time entries to specific projects with various rates and activities

## Setup

### Prerequisites

- Python 3.10 or higher
- The MCP framework (`pip install mcp`)
- An Insider account with API access

### Environment Variables

Set the following environment variables before running the server:

```bash
export INSIDER_AUTH_TOKEN="your-bearer-token-here"
export INSIDER_USER_ID="your-user-id"
export INSIDER_EMP_CODE="your-employee-code"
```

### Installation

1. Clone this repository
2. Install the package:

```bash
pip install -e .
```

## Usage

### Running the Server

```bash
python -m timesheet_mcp
```

### Tool: list_projects

Lists all projects available to the user.

```json
{
  "name": "list_projects",
  "arguments": {}
}
```

Response:
```json
{
  "projects": [
    {
      "id": 10522,
      "name": "Project Name"
    },
    ...
  ]
}
```

### Tool: log_time_project

Logs time to a specific project.

```json
{
  "name": "log_time_project",
  "arguments": {
    "projectId": 10522,
    "hours": 4,
    "logDate": "2025-05-29",
    "hourRate": 1.5,
    "activity": 1,
    "comment": "Working on feature X"
  }
}
```

Parameters:
- `projectId` (required): Project ID from list_projects
- `hours` (required): Number of hours to log (between 0.5 and 24)
- `logDate` (required): Date to log time for in YYYY-MM-DD format
- `hourRate` (optional, default: 1.0): Hour rate (1 for normal, 1.5 for OT weekday, 2 for OT weekend, 3 for OT holiday)
- `activity` (optional, default: 1): Activity type (1 for Code, 2 for Test)
- `comment` (optional): Comment for the time entry

Response:
```json
{
  "success": true,
  "message": "Time logged successfully",
  "details": {
    "id": 12345,
    "status": "success"
  }
}
```

## Running Tests

```bash
python -m unittest discover tests
```

## License

MIT