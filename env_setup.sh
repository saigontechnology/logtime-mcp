#!/bin/bash

# This script helps set up the environment variables for the Timesheet MCP server

echo "Setting up environment variables for Timesheet MCP server"

# Prompt user for values
echo -n "Enter your Insider Auth Token (Bearer token without 'Bearer '): "
read -r auth_token

echo -n "Enter your User ID: "
read -r user_id

echo -n "Enter your Employee Code: "
read -r emp_code

# Export the variables to the current shell session
export INSIDER_AUTH_TOKEN="$auth_token"
export INSIDER_USER_ID="$user_id"
export INSIDER_EMP_CODE="$emp_code"

echo
echo "Environment variables set successfully!"
echo
echo "To use them in a new terminal, paste the following:"
echo "export INSIDER_AUTH_TOKEN=\"$auth_token\""
echo "export INSIDER_USER_ID=\"$user_id\""
echo "export INSIDER_EMP_CODE=\"$emp_code\""
echo
echo "To test the MCP server, run:"
echo "./run_mcp.sh"
echo
echo "To test with the client, run:"
echo "python test_client.py list_projects"
echo "python test_client.py log_time PROJECT_ID HOURS LOG_DATE"