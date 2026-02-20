from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai_tools.adapters.mcp_adapter import MCPServerAdapter
from mcp import StdioServerParameters
import os
from .tools.custom_tool import CandidateJSONParserTool
import yaml

@CrewBase
class ExtractCrew():
    """Talentcopilot crew"""

    agents: List[BaseAgent]
    tasks: List[Task]
  
  
    def __init__(self):
        with open("src/talentcopilot/config/llm_config_.yaml") as f:
            config = yaml.safe_load(f)
        groq_cfg = config["groq"]

        print(groq_cfg, "Groq LLM Config", "api_key", os.getenv(groq_cfg["api_key_env"]))

        self.groq_llm = LLM(
            model=groq_cfg["model"],
            temperature=groq_cfg["temperature"],
            api_key=os.getenv(groq_cfg["api_key_env"]),
            base_url=groq_cfg["base_url"],
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



    @crew
    def crew(self) -> Crew:
        """Creates the Talentcopilot crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=[self.data_extractor()], # Automatically created by the @agent decorator
            tasks=[self.extract_data()], # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
        
if __name__ == "__main__":
    crew = Talentcopilot().crew()
    result = crew.kickoff()
    print(result)
    print("Talentcopilot Crew Test Completed.")