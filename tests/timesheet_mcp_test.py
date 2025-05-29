import unittest
import json
import os
import sys
import asyncio
import tempfile
from contextlib import AsyncExitStack
from unittest.mock import patch, MagicMock

try:
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client
except ImportError as e:
    print(f"ERROR: Could not import mcp components. Ensure mcp library is installed correctly. {e}")
    sys.exit(1)

# Path to the MCP script - adjusted for actual file structure
MCP_SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "timesheet_mcp", "main.py"))

# Sample test data
MOCK_PROJECTS_RESPONSE = [{
    "12": {
        "id": 10522,
        "client": {"id": 5372, "name": "Fusang SSO PoC"},
        "color": "133A5E",
        "projectModel": 2,
        "name": "Fusang SSO PoC",
        "startDate": "2020-04-30T00:00:00Z",
        "endDate": "2020-08-03T06:47:04.736Z",
        "code": "SSO-POC"
    }
}]

MOCK_LOG_TIME_RESPONSE = {
    "id": 12345,
    "status": "success",
    "message": "Time logged successfully"
}

class TestTimesheetMCP(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Set up environment variables for tests
        os.environ["INSIDER_AUTH_TOKEN"] = "test_token"
        os.environ["INSIDER_USER_ID"] = "186"
        os.environ["INSIDER_EMP_CODE"] = "test.user"
        
        # Define server parameters for tests
        server_env = os.environ.copy()
        cls.server_params = StdioServerParameters(
            command=sys.executable,
            args=[MCP_SCRIPT_PATH],
            env=server_env,
        )
    
    @patch('requests.get')
    async def test_list_projects(self, mock_get):
        # Configure mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_PROJECTS_RESPONSE
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(self.server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            # Test listing tools first
            tools_response = await session.list_tools()
            self.assertEqual(len(tools_response.tools), 2)
            self.assertEqual(tools_response.tools[0].name, "list_projects")
            self.assertEqual(tools_response.tools[1].name, "log_time_project")
            
            # Test list_projects tool
            result = await session.call_tool("list_projects", {})
            
            # Verify mock was called correctly
            mock_get.assert_called_once()
            self.assertTrue("Bearer test_token" in mock_get.call_args[1]["headers"]["Authorization"])
            
            # Verify result
            self.assertFalse(result.isError)
            content = json.loads(result.content[0].text)
            self.assertIn("projects", content)
            self.assertEqual(len(content["projects"]), 1)
            self.assertEqual(content["projects"][0]["id"], 10522)
            self.assertEqual(content["projects"][0]["name"], "Fusang SSO PoC")
    
    @patch('requests.post')
    async def test_log_time_project(self, mock_post):
        # Configure mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_LOG_TIME_RESPONSE
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(self.server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            # Test log_time_project tool
            tool_args = {
                "projectId": 10522,
                "hours": 4,
                "logDate": "2025-05-29",
                "hourRate": 1.5,  # OT weekday
                "activity": 1,  # Code
                "comment": "Working on feature X"
            }
            
            result = await session.call_tool("log_time_project", tool_args)
            
            # Verify mock was called correctly
            mock_post.assert_called_once()
            self.assertTrue("Bearer test_token" in mock_post.call_args[1]["headers"]["Authorization"])
            
            payload = mock_post.call_args[1]["json"]
            self.assertEqual(payload["userId"], 186)  # From environment
            self.assertEqual(payload["empCode"], "test.user")  # From environment
            self.assertEqual(payload["projectId"], 10522)
            self.assertEqual(payload["hours"], 4)
            self.assertEqual(payload["hourRate"], 1.5)
            self.assertEqual(payload["activity"], 1)
            self.assertEqual(payload["comment"], "Working on feature X")
            
            # Verify result
            self.assertFalse(result.isError)
            content = json.loads(result.content[0].text)
            self.assertTrue(content["success"])
            self.assertEqual(content["message"], "Time logged successfully")
    
    @patch('requests.post')
    async def test_log_time_project_validation_error(self, mock_post):
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(self.server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            # Test with invalid hour rate
            tool_args = {
                "projectId": 10522,
                "hours": 4,
                "logDate": "2025-05-29",
                "hourRate": 2.5,  # Invalid rate (not in [1, 1.5, 2, 3])
                "activity": 1
            }
            
            result = await session.call_tool("log_time_project", tool_args)
            
            # Expect validation error
            self.assertTrue(result.isError)
            content = json.loads(result.content[0].text)
            self.assertIn("error", content)
            self.assertIn("hourRate", content["error"])
            
            # Mock should not be called due to validation error
            mock_post.assert_not_called()
    
    @patch('requests.post')
    async def test_log_time_project_api_error(self, mock_post):
        # Simulate API error
        mock_post.side_effect = Exception("API Error")
        
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(self.server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            tool_args = {
                "projectId": 10522,
                "hours": 4,
                "logDate": "2025-05-29",
                "hourRate": 1,
                "activity": 1
            }
            
            result = await session.call_tool("log_time_project", tool_args)
            
            # Expect error from API
            self.assertTrue(result.isError)
            content = json.loads(result.content[0].text)
            self.assertIn("error", content)
            self.assertIn("API Error", content["error"])
    
    async def test_unknown_tool(self):
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(self.server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            result = await session.call_tool("unknown_tool", {})
            
            # Expect unknown tool error
            self.assertTrue(result.isError)
            content = json.loads(result.content[0].text)
            self.assertIn("error", content)
            self.assertIn("Unknown tool", content["error"])

if __name__ == "__main__":
    unittest.main()