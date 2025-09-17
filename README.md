# Timesheet MCP Server

An MCP (Model Context Protocol) server for logging time to the Insider system.

## Features

- List all projects available to the user
- Log time entries to specific projects with various rates and activities
- List invalid days that don't meet the required 8-hour working time

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
    "logDates": ["2025-05-29"],
    "hourRate": 1.5,
    "activity": 1,
    "comment": "Working on feature X"
  }
}
```

Parameters:

- `projectId` (required): Project ID from list_projects
- `hours` (required): Number of hours to log (between 0.5 and 8)
- `logDates` (required): List of Dates to log time for in YYYY-MM-DD format
- `hourRate` (optional, default: 1): Hour rate (1 for normal, 2 for OT weekday, 3 for OT weekend, 4 for OT holiday)
- `activity` (optional, default: 1): Activity type (1 for Code, 2 for Test)
- `comment` (optional): Comment for the time entry

Response:

```json
{
  "success": true,
  "message": "Time logged successfully",
  "details": {
    "status": "success"
  }
}
```

### Tool: list_invalid_days

Lists all invalid days that don't meet the required 8-hour working time for a specific month.

```json
{
  "name": "list_invalid_days",
  "arguments": {
    "year": 2025,
    "month": 9
  }
}
```

Parameters:

- `year` (required): Year to check (between 2020 and current year + 1)
- `month` (required): Month to check (1-12)

Response: Returns a markdown formatted report showing:

- Total number of invalid days
- For each invalid day:
  - Date and current logged hours vs expected hours  
  - Shortfall in hours
  - Working day status and holiday status
  - Detailed invalid message
  - Current log entries with project names and hours

Example output:
```markdown
# Invalid Days for 2025-09

**Total Invalid Days:** 2

## 2025-09-03
- **Current Hours:** 6.0h
- **Expected Hours:** 8.0h
- **Shortfall:** 2.0h
- **Working Day:** Yes
- **Holiday:** No
- **Issue:** This is normal working day so there should be exact 8 hours log time with hour rate 1.0 in this day.
- **Current Log Entries:**
  - AxiaGram: 6.0h (Working on feature)

## 2025-09-04
- **Current Hours:** 0.0h
- **Expected Hours:** 8.0h
- **Shortfall:** 8.0h
- **Working Day:** Yes
- **Holiday:** No
- **Issue:** This is normal working day so there should be exact 8 hours log time with hour rate 1.0 in this day.
- **Current Log Entries:** None
```

## Testing

### Running Unit Tests

```bash
uv run python -m unittest tests.timesheet_mcp_test -v
```

### Manual Testing with Test Client

```bash
# List projects
uv run python test_client.py list_projects

# Log time to a project
uv run python test_client.py log_time 10522 8 2025-09-17 1 1 "Working on new feature"

# List invalid days for a specific month
uv run python test_client.py list_invalid_days 2025 9
```

### Manual Logic Testing

```bash
# Test the filtering logic without hitting the real API
uv run python manual_test.py
```

## License

MIT

