import os
import json
import logging
import asyncio
import datetime
from typing import Dict, List, Optional, Any, Union

import requests
from pydantic import BaseModel, Field, field_validator
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# --- Configuration ---
API_BASE_URL = "https://insiderapi.saigontechnology.vn/api"
AUTH_TOKEN_ENV = "INSIDER_AUTH_TOKEN"
USER_ID_ENV = "INSIDER_USER_ID"
EMP_CODE_ENV = "INSIDER_EMP_CODE"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Model Definitions ---
class ListProjectsInput(BaseModel):
    pass  # No input needed for list_projects


class ListInvalidDaysInput(BaseModel):
    year: int = Field(..., description="Year to check (e.g., 2025)")
    month: int = Field(..., description="Month to check (1-12)", ge=1, le=12)

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        current_year = datetime.datetime.now().year
        if v < 2020 or v > current_year + 1:
            raise ValueError(f"Year must be between 2020 and {current_year + 1}")
        return v


class LogTimeInput(BaseModel):
    projectId: int = Field(..., description="Project ID from list_project")
    hours: float = Field(..., description="Number of hours to log", ge=0.5, le=8)
    logDates: List[str] = Field(
        ..., description="List of dates to log time for in YYYY-MM-DD format"
    )
    hourRate: int = Field(
        1,
        description="Hour rate: 1 for normal, 2 for OT weekday, 3 for OT weekend, 4 for OT holiday",
    )
    activity: int = Field(1, description="Activity type: 1 for Code, 2 for Test")
    comment: Optional[str] = Field(
        "", description="Optional comment for the time entry"
    )

    # @validator("logDate")
    # def validate_date_format(cls, v):
    #     try:
    #         datetime.datetime.strptime(v, "%Y-%m-%d")
    #         return v
    #     except ValueError:
    #         raise ValueError("logDate must be in YYYY-MM-DD format")
    #
    # @validator("hourRate")
    # def validate_hour_rate(cls, v):
    #     valid_rates = [1.0, 1.5, 2.0, 3.0]
    #     if v not in valid_rates:
    #         raise ValueError(f"hourRate must be one of {valid_rates}")
    #     return v
    #
    # @validator("activity")
    # def validate_activity(cls, v):
    #     valid_activities = [1, 2]
    #     if v not in valid_activities:
    #         raise ValueError(f"activity must be one of {valid_activities}")
    #     return v


class Project(BaseModel):
    id: int
    name: str


# --- API Service Class ---
class InsiderAPIService:
    def __init__(self, auth_token: str, user_id: str, emp_code: str):
        self.auth_token = auth_token
        self.user_id = user_id
        self.emp_code = emp_code
        self.base_url = API_BASE_URL

        # Validate credentials
        if not auth_token:
            raise ValueError(
                f"Auth token not provided ({AUTH_TOKEN_ENV} environment variable)"
            )
        if not user_id:
            raise ValueError(
                f"User ID not provided ({USER_ID_ENV} environment variable)"
            )
        if not emp_code:
            raise ValueError(
                f"Employee code not provided ({EMP_CODE_ENV} environment variable)"
            )

    def _get_auth_headers(self):
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "User-Agent": "MCP-Client/1.0",
            "Accept": "application/json, text/plain, */*",
        }

    def list_projects(self) -> List[Project]:
        """Fetch all projects for the user"""
        endpoint = f"{self.base_url}/project/get-basic/user/{self.user_id}"

        try:
            response = requests.get(endpoint, headers=self._get_auth_headers())
            response.raise_for_status()

            # Parse JSON response - which has numeric keys as top level
            projects_data = response.json()
            projects = []

            for project_data in projects_data:
                projects.append(
                    Project(id=project_data["id"], name=project_data["name"])
                )

            return projects

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch projects: {e}")
            # Try to get error details if available
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("message", str(error_data))
                except:
                    error_detail = e.response.text

            raise RuntimeError(f"Failed to fetch projects: {error_detail}")

    def log_time(self, log_time_input: LogTimeInput) -> Dict[str, Any]:
        """Log time for a project"""
        endpoint = f"{self.base_url}/timesheet/add"
        result = []

        for date in log_time_input.logDates:
            payload = {
                "userId": int(self.user_id),
                "empCode": self.emp_code,
                "logDate": date,
                "hours": log_time_input.hours,
                "hourRate": log_time_input.hourRate,
                "activity": log_time_input.activity,
                "projectId": log_time_input.projectId,
                "inquiryId": None,
                "milestoneId": None,
                "comment": log_time_input.comment,
            }
            logger.info(payload)

            try:
                response = requests.post(
                    endpoint, headers=self._get_auth_headers(), json=payload
                )
                response.raise_for_status()

                result.append(
                    f"Project: {log_time_input.projectId}, date: {date}, status: done"
                )

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to log time: {e}")
                # Try to get error details if available
                error_detail = str(e)
                if hasattr(e, "response") and e.response is not None:
                    try:
                        error_data = e.response.json()
                        error_detail = error_data.get("message", str(error_data))
                    except:
                        error_detail = e.response.text

                raise RuntimeError(f"Failed to log time: {error_detail}")
        return {"result": result}

    def list_invalid_days(self, year: int, month: int) -> Dict[str, Any]:
        """Get list of invalid days (not enough 8h per day) for a specific month"""
        # Calculate first and last day of the month
        first_date = datetime.date(year, month, 1)
        
        # Calculate last day of the month
        if month == 12:
            last_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            last_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
        # Format dates as required by API
        first_date_str = first_date.strftime("%Y-%m-%d")
        last_date_str = last_date.strftime("%Y-%m-%d")
        
        endpoint = f"{self.base_url}/timesheet/{self.emp_code}/timesheetCalendar/{first_date_str}/{last_date_str}"
        
        try:
            response = requests.get(endpoint, headers=self._get_auth_headers())
            response.raise_for_status()
            
            # Parse JSON response
            calendar_data = response.json()
            
            # Filter invalid days
            invalid_days = []
            for day_data in calendar_data:
                if not day_data.get("isValid", True):  # Default to True if isValid field is missing
                    # Calculate total logged hours for this day
                    total_hours = sum(log_time.get("hours", 0) for log_time in day_data.get("logTimes", []))
                    
                    invalid_day_info = {
                        "date": day_data["logDate"][:10],  # Extract just the date part (YYYY-MM-DD)
                        "invalidMessage": day_data.get("invalidMessage", "No message provided"),
                        "currentLoggedHours": total_hours,
                        "expectedHours": 8.0,
                        "shortfall": 8.0 - total_hours,
                        "isNormalWorkingDay": day_data.get("isNormalWorkingDay", False),
                        "isPublicHoliday": day_data.get("isPublicHoliday", False),
                        "logTimes": day_data.get("logTimes", [])
                    }
                    invalid_days.append(invalid_day_info)
            
            return {
                "month": f"{year}-{month:02d}",
                "totalInvalidDays": len(invalid_days),
                "invalidDays": invalid_days
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch timesheet calendar: {e}")
            # Try to get error details if available
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("message", str(error_data))
                except:
                    error_detail = e.response.text
            
            raise RuntimeError(f"Failed to fetch timesheet calendar: {error_detail}")


# --- MCP Server Implementation ---
async def serve() -> None:
    logger.info("Initializing Timesheet MCP server...")
    server = Server("mcp-timesheet")

    # Get environment variables early to validate configuration
    auth_token = os.environ.get(AUTH_TOKEN_ENV, "")
    user_id = os.environ.get(USER_ID_ENV, "")
    emp_code = os.environ.get(EMP_CODE_ENV, "")

    # Validate required environment variables
    if not all([auth_token, user_id, emp_code]):
        missing_vars = []
        if not auth_token:
            missing_vars.append(AUTH_TOKEN_ENV)
        if not user_id:
            missing_vars.append(USER_ID_ENV)
        if not emp_code:
            missing_vars.append(EMP_CODE_ENV)

        error_message = (
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        logger.error(error_message)

        # We'll continue but will report errors when tools are called

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        logger.info("Listing available tools")
        return [
            Tool(
                name="list_projects",
                description="Get a list of all available projects for the user in markdown format",
                inputSchema=ListProjectsInput.model_json_schema(),
            ),
            Tool(
                name="log_time_project",
                description="Log time to a specific project",
                inputSchema=LogTimeInput.model_json_schema(),
            ),
            Tool(
                name="list_invalid_days",
                description="List all invalid log days (not enough 8h per day) for a specific month",
                inputSchema=ListInvalidDaysInput.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")

        try:
            # Create service outside specific tool handling to validate env vars early
            try:
                service = InsiderAPIService(auth_token, user_id, emp_code)
            except ValueError as e:
                raise RuntimeError(f"Service initialization failed: {str(e)}")

            if name == "list_projects":
                # No input validation needed for list_projects

                # Run the potentially blocking API call in an executor
                loop = asyncio.get_running_loop()
                projects = await loop.run_in_executor(None, service.list_projects)

                # Convert to markdown format
                markdown_output = "# Available Projects\n\n"

                if projects:
                    for project in projects:
                        markdown_output += f"- **{project.name}** (ID: {project.id})\n"
                else:
                    markdown_output += "No projects found.\n"

                return [
                    TextContent(
                        type="text",
                        text=markdown_output,
                    )
                ]

            elif name == "log_time_project":
                # Validate input using Pydantic model
                log_time_input = LogTimeInput(**arguments)

                # Run the potentially blocking API call in an executor
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None, lambda: service.log_time(log_time_input)
                )

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "message": "Time logged successfully",
                                "details": result,
                            }
                        ),
                    )
                ]

            elif name == "list_invalid_days":
                # Validate input using Pydantic model
                list_invalid_days_input = ListInvalidDaysInput(**arguments)
                
                # Run the potentially blocking API call in an executor
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None, lambda: service.list_invalid_days(
                        list_invalid_days_input.year, 
                        list_invalid_days_input.month
                    )
                )
                
                # Format output as readable text
                output_text = f"# Invalid Days for {result['month']}\n\n"
                output_text += f"**Total Invalid Days:** {result['totalInvalidDays']}\n\n"
                
                if result['invalidDays']:
                    for day in result['invalidDays']:
                        output_text += f"## {day['date']}\n"
                        output_text += f"- **Current Hours:** {day['currentLoggedHours']:.1f}h\n"
                        output_text += f"- **Expected Hours:** {day['expectedHours']:.1f}h\n"
                        output_text += f"- **Shortfall:** {day['shortfall']:.1f}h\n"
                        output_text += f"- **Working Day:** {'Yes' if day['isNormalWorkingDay'] else 'No'}\n"
                        output_text += f"- **Holiday:** {'Yes' if day['isPublicHoliday'] else 'No'}\n"
                        output_text += f"- **Issue:** {day['invalidMessage']}\n"
                        
                        if day['logTimes']:
                            output_text += f"- **Current Log Entries:**\n"
                            for log_entry in day['logTimes']:
                                project_name = log_entry.get('projectName', 'Unknown Project')
                                hours = log_entry.get('hours', 0)
                                comment = log_entry.get('comment', 'No comment')
                                output_text += f"  - {project_name}: {hours}h ({comment})\n"
                        else:
                            output_text += f"- **Current Log Entries:** None\n"
                        output_text += "\n"
                else:
                    output_text += "No invalid days found for this month! 🎉\n"
                
                return [
                    TextContent(
                        type="text",
                        text=output_text,
                    )
                ]

            else:
                logger.error(f"Unknown tool: {name}")
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            error_result = {"error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_result))]

    # Run the server using stdio
    logger.info("Starting Timesheet MCP server...")
    options = server.create_initialization_options()

    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server started. Waiting for requests...")
            await server.run(read_stream, write_stream, options, raise_exceptions=False)
    except Exception as e:
        logger.exception("Critical server error")
    finally:
        logger.info("Server shutdown")


def main():
    """Entry point for the MCP server."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.exception("Critical server error in main function")


if __name__ == "__main__":
    main()
