#!/usr/bin/env python3
"""
Test client for Timesheet MCP server.
This script demonstrates how to interact with the MCP server directly.

Usage:
    python test_client.py list_projects
    python test_client.py log_time PROJECT_ID HOURS LOG_DATE [HOUR_RATE] [ACTIVITY] [COMMENT]
    python test_client.py list_invalid_days YEAR MONTH

Example:
    python test_client.py list_projects
    python test_client.py log_time 10522 8 2025-05-29 2 1 "Working on feature X"
    python test_client.py list_invalid_days 2025 9

Note: list_projects and list_invalid_days return markdown format.
"""

import os
import sys
import json
import asyncio
import subprocess
from contextlib import AsyncExitStack

try:
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: MCP library not found. Please install it with 'pip install mcp'")
    sys.exit(1)

# Path to the MCP script
MCP_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "src", "timesheet_mcp", "main.py"
)


async def call_list_projects():
    """List all available projects"""
    server_env = os.environ.copy()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[MCP_SCRIPT_PATH],
        env=server_env,
    )

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read, write))

        print("Initializing session...")
        await session.initialize()

        print("Calling list_projects tool...")
        result = await session.call_tool("list_projects", {})

        if result.isError:
            # Try to parse as JSON for error, but it might be plain text
            try:
                error_content = json.loads(result.content[0].text)
                print("Error:", error_content)
            except json.JSONDecodeError:
                print("Error:", result.content[0].text)
            return 1

        # The content is now in markdown format, not JSON
        markdown_content = result.content[0].text

        print("\nReceived markdown response:")
        print("=" * 50)
        print(markdown_content)

        return 0


async def call_log_time(
    project_id, hours, log_date, hour_rate=1.0, activity=1, comment=""
):
    """Log time to a specific project"""
    server_env = os.environ.copy()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[MCP_SCRIPT_PATH],
        env=server_env,
    )

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read, write))

        print("Initializing session...")
        await session.initialize()

        tool_args = {
            "projectId": int(project_id),
            "hours": float(hours),
            "logDates": [log_date],  # Changed to list format as expected by the model
            "hourRate": int(hour_rate),
            "activity": int(activity),
            "comment": comment,
        }

        print(f"Logging {hours} hours to project ID {project_id} on {log_date}...")
        result = await session.call_tool("log_time_project", tool_args)

        if result.isError:
            print("Error:", json.loads(result.content[0].text))
            return 1

        content = json.loads(result.content[0].text)
        print("\nSuccess:", content.get("message"))
        print("Details:", json.dumps(content.get("details", {}), indent=2))

        return 0


async def call_list_invalid_days(year, month):
    """List invalid days for a specific month"""
    server_env = os.environ.copy()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[MCP_SCRIPT_PATH],
        env=server_env,
    )
    year = int(year)
    month = int(month)

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read, write))

        print("Initializing session...")
        await session.initialize()

        tool_args = {"year": int(year), "month": int(month)}

        print(f"Getting invalid days for {year}-{month:02d}...")
        result = await session.call_tool("list_invalid_days", tool_args)

        if result.isError:
            # Try to parse as JSON for error, but it might be plain text
            try:
                error_content = json.loads(result.content[0].text)
                print("Error:", error_content)
            except json.JSONDecodeError:
                print("Error:", result.content[0].text)
            return 1

        # The content is in markdown format
        markdown_content = result.content[0].text

        print("\nReceived markdown response:")
        print("=" * 50)
        print(markdown_content)

        return 0


def show_usage():
    """Show usage information"""
    print("Usage:")
    print("  python test_client.py list_projects")
    print(
        "  python test_client.py log_time PROJECT_ID HOURS LOG_DATE [HOUR_RATE] [ACTIVITY] [COMMENT]"
    )
    print("  python test_client.py list_invalid_days YEAR MONTH")
    print("\nExamples:")
    print("  python test_client.py list_projects")
    print(
        '  python test_client.py log_time 10522 8 2025-05-29 2 1 "Working on feature X"'
    )
    print("  python test_client.py list_invalid_days 2025 9")
    print("\nNote: list_projects and list_invalid_days return markdown format.")
    sys.exit(1)


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_usage()

    command = sys.argv[1]

    # Check environment variables
    required_vars = ["INSIDER_AUTH_TOKEN", "INSIDER_USER_ID", "INSIDER_EMP_CODE"]
    missing = [var for var in required_vars if not os.environ.get(var)]

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("\nPlease set the following environment variables:")
        for var in missing:
            print(f"  export {var}=your-value-here")
        return 1

    if command == "list_projects":
        return await call_list_projects()
    elif command == "log_time":
        if len(sys.argv) < 5:
            print("Error: Not enough arguments for log_time command")
            show_usage()

        project_id = sys.argv[2]
        hours = sys.argv[3]
        log_date = sys.argv[4]
        hour_rate = sys.argv[5] if len(sys.argv) > 5 else 1.0
        activity = sys.argv[6] if len(sys.argv) > 6 else 1
        comment = sys.argv[7] if len(sys.argv) > 7 else ""

        return await call_log_time(
            project_id, hours, log_date, hour_rate, activity, comment
        )
    elif command == "list_invalid_days":
        if len(sys.argv) < 4:
            print("Error: Not enough arguments for list_invalid_days command")
            show_usage()

        year = sys.argv[2]
        month = sys.argv[3]

        return await call_list_invalid_days(year, month)
    else:
        print(f"Error: Unknown command '{command}'")
        show_usage()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
