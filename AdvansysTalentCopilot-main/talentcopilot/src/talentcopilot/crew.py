from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai_tools.adapters.mcp_adapter import MCPServerAdapter
from mcp import StdioServerParameters
import os
from .tools.custom_tool import CandidateJSONParserTool
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

# server_paramas=StdioServerParameters(
#     command="python3",
#     args=["C:\Users\abdal\Desktop\InternProject\talentcopilot\postgres-file\postgres-demo.py"],
#     env={"UV_PYTHON": "3.12", **os.environ},
# )


# with MCPServerAdapter(server_paramas) as tools:

    # print(f"Available tools from Stdio MCP server: {[tool.name for tool in tools]}")




@CrewBase
class Talentcopilot():
    """Talentcopilot crew"""

    agents: List[BaseAgent]
    tasks: List[Task]


    mcp_server_params = [
    # # Streamable HTTP Server
    # {
    #     "url": "http://localhost:8001/mcp",
    #     "transport": "streamable-http"
    # },
    # # SSE Server
    # {
    #     "url": "http://localhost:8000/sse",
    #     "transport": "sse"
    # },
    # StdIO Server
    StdioServerParameters(
        command="python",
        args=["postgres-file/postgres-demo.py"],
        env={"UV_PYTHON": "3.12", **os.environ},
    )
  ]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    # @agent
    # def DatabaseManager(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['DatabaseManager'], # type: ignore[index]
    #         tools=self.get_mcp_tools("insert_data", "select_data", "delete_data", "update_data"), # Pass the loaded tools to your agent
    #         verbose=True
    #     )

    @agent
    def Inserter(self) -> Agent:
        return Agent(
            config=self.agents_config['Inserter'], # type: ignore[index]
            tools=self.get_mcp_tools("insert_data"), # Pass the loaded tools to your agent
            verbose=True
        )

    @agent
    def Updater(self) -> Agent:
        return Agent(
            config=self.agents_config['Updater'], # type: ignore[index]
            tools=self.get_mcp_tools("update_data"), # Pass the loaded tools to your agent
            verbose=True
        )

    @agent
    def Reader(self) -> Agent:
        return Agent(
            config=self.agents_config['Reader'], # type: ignore[index]
            tools=self.get_mcp_tools("select_data"), # Pass the loaded tools to your agent
            verbose=True
        )

    @agent
    def Deleter(self) -> Agent:
        return Agent(
            config=self.agents_config['Deleter'], # type: ignore[index]
            tools=self.get_mcp_tools("delete_data"), # Pass the loaded tools to your agent
            verbose=True
        )

    @agent
    def DatabaseManager(self) -> Agent:
        return Agent(
            config=self.agents_config['DatabaseManager'], # type: ignore[index]
            verbose=True,
            allow_delegation=True
        )



    @agent
    def data_extractor(self) -> Agent:
        return Agent(
            config=self.agents_config['data_extractor'], # type: ignore[index]
            tools=[CandidateJSONParserTool()],
            verbose=True,
            llm=self.groq_llm,
            allow_delegation= False
        )

    @task
    def extract_data(self) -> Task:
        return Task(
            config=self.tasks_config['extract_data'],  # type: ignore[index]
            agent=self.data_extractor()
        )
   

    
    
    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    # @task
    # def database_task(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['Database_task'], # type: ignore[index]
    #     )

    @task
    def Insert_task(self) -> Task:
        return Task(
            config=self.tasks_config['Insert_task'], # type: ignore[index]
            agent=self.Inserter()

        )

    @task
    def Get_task(self) -> Task:
        return Task(
            config=self.tasks_config['Get_task'], # type: ignore[index]
            agent=self.Reader()

        )

    @task
    def Update_task(self) -> Task:
        return Task(
            config=self.tasks_config['Update_task'], # type: ignore[index]
            agent=self.Updater()

        )

    @task
    def Delete_task(self) -> Task:
        return Task(
            config=self.tasks_config['Delete_task'], # type: ignore[index]
            agent=self.Deleter()

        )

    @task
    def DatabaseManager_task(self) -> Task:
        return Task(
            config=self.tasks_config['Database_Routing_Task'], # type: ignore[index]
            agent=self.DatabaseManager()
        )





    @crew
    def crew(self) -> Crew:
        """Creates the Talentcopilot crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=[self.Inserter(), self.Updater(), self.Reader(), self.Deleter(), self.data_extractor()], # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            manager_agent=self.DatabaseManager(),
            process=Process.hierarchical,
            planning=True,
            verbose=True,
        )

