"""Temporary script to probe the strands MCPClient + Agent API."""
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.stdio import StdioServerParameters, stdio_client

params = StdioServerParameters(command="aind-data-mcp", args=[])
mcp_client = MCPClient(lambda: stdio_client(params))

model = BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")
with mcp_client:
    tools = mcp_client.list_tools_sync()
    print(f"Got {len(tools)} tools: {[t.tool_name for t in tools]}")
    agent = Agent(model=model, tools=tools)
    response = agent("How many records are stored in the database?")
    print("ANSWER:", str(response)[:500])
