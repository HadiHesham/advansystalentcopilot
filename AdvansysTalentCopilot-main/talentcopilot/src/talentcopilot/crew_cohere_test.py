import os
import yaml
from crewai import LLM, Agent, Crew, Task
from crewai.project import CrewBase, agent, crew, task
from dotenv import load_dotenv

load_dotenv()

@CrewBase
class CohereTestCrew:
    """A test crew to verify Cohere LLM integration."""

    def __init__(self):
        with open("src/talentcopilot/config/llm_config.yaml") as f:
            config = yaml.safe_load(f)
        cohere_cfg = config["cohere"]

        print(cohere_cfg, "Cohere LLM Config", "api_key", os.getenv(cohere_cfg["api_key_env"]))
        self.cohere_llm = LLM(
            model=cohere_cfg["model"],
            temperature=cohere_cfg["temperature"],
            api_key=os.getenv(cohere_cfg["api_key_env"]),
        )

    @agent
    def cohere_tester(self) -> Agent:
        """An agent to test Cohere LLM."""
        return Agent(
            role="Cohere Tester",
            goal="Say hello and confirm Cohere is working.",
            backstory="You are a test agent to verify Cohere LLM integration.",
            llm=self.cohere_llm,
            verbose=True
        )

    @task
    def cohere_test_task(self) -> Task:
        """A task to test Cohere LLM."""
        return Task(
            description="Say hello and tell me which LLM you are using.",
            agent=self.cohere_tester(),
            expected_output="Hello, I am using Cohere LLM."
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Cohere test crew."""
        return Crew(
            agents=[self.cohere_tester()],
            tasks=[self.cohere_test_task()],
            verbose=True
        )

if __name__ == "__main__":
    CohereTestCrew().crew().kickoff()
    print("Cohere Crew Test Completed.")