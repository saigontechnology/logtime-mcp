#!/bin/bash

# This script runs the Timesheet MCP server

# Check if the environment variables are set
if [ -z "$INSIDER_AUTH_TOKEN" ]; then
    echo "Error: INSIDER_AUTH_TOKEN environment variable is not set"
    echo "Please run: export INSIDER_AUTH_TOKEN=your-token-here"
    exit 1
fi

if [ -z "$INSIDER_USER_ID" ]; then
    echo "Error: INSIDER_USER_ID environment variable is not set"
    echo "Please run: export INSIDER_USER_ID=your-user-id"
    exit 1
fi

if [ -z "$INSIDER_EMP_CODE" ]; then
    echo "Error: INSIDER_EMP_CODE environment variable is not set"
    echo "Please run: export INSIDER_EMP_CODE=your-employee-code"
    exit 1
fi

# Run the MCP server
echo "Starting Timesheet MCP server..."
python -m src.timesheet_mcp.main