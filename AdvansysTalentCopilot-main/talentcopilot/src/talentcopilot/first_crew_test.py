import os
import yaml
import json
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileReadTool
from dotenv import load_dotenv
from .tools.cv_parser_tools import (
    file_type_validator_tool, 
    pdf_text_extractor_tool,
    pdf_error_logger_tool,
    pdf_validation_tool
)

load_dotenv()

@CrewBase
class CVProcessingCrew:
    """A crew for processing and analyzing CV/resume documents."""

    def __init__(self):        
        # Set dummy OpenAI key if required by some tools
        # Rage3 el heta deeh bardo
        os.environ["OPENAI_API_KEY"] = "sk-dummy-key-not-used" 
        
        # Load configuration files
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, 'config')
        
        files = {
            'agents': os.path.join(config_dir, 'agents.yaml'),
            'tasks': os.path.join(config_dir, 'tasks.yaml')
        }
        
        print("Script directory:", script_dir)
        print("Config directory:", config_dir)
        print("Files dict:", files)
        
        configs = {}
        for config_type, file_path in files.items():
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Configuration file {file_path} not found")
            with open(file_path, 'r') as file:
                configs[config_type] = yaml.safe_load(file)

        print("Loaded tasks_config keys:", list(configs['tasks'].keys()))
        
        self.agents_config = configs['agents']
        self.tasks_config = configs['tasks']
        
        # Initialize tools
        self.file_read_tool = FileReadTool()
        
        # self.cohere_llm = LLM(
        #     model="cohere/command-r-plus",
        #     temperature=0.7,
        #     api_key=os.getenv("COHERE_API_KEY")
        # )
        # self.groq_llm = LLM(model="groq/llama-3.3-70b-versatile")
        # self.gemini_llm = LLM(model="gemini/gemini-1.5-flash")
        # self.together_llm = LLM(
        #     model="together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
        #     base_url="https://api.together.xyz/v1"
        # )

    @agent
    def file_validator_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['file_validator'],
            # llm=self.gemini_llm,
            tools=[
                self.file_read_tool,       
                file_type_validator_tool,
            ],
            verbose=True
        )

    @agent
    def pdf_processor_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['pdf_processor'],
            # llm=self.together_llm,
            tools=[
                self.file_read_tool,
                pdf_text_extractor_tool,
                pdf_error_logger_tool,
                pdf_validation_tool
            ],
            verbose=True
        )

    @agent
    def entity_formatter_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['entity_formatter'],
            # llm=self.cohere_llm,
            tools=[self.file_read_tool],
            verbose=True
        )

    @task
    def validate_and_classify_task(self) -> Task:
        return Task(
            config=self.tasks_config['validate_and_classify_task'],
            agent=self.file_validator_agent()
        )

    @task
    def error_reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config['error_reporting_task'],
            agent=self.file_validator_agent(),
            context=[self.validate_and_classify_task()]
        )

    @task
    def pdf_text_extraction_task(self) -> Task:
        return Task(
            config=self.tasks_config['pdf_text_extraction_task'],
            agent=self.pdf_processor_agent(),
            context=[self.validate_and_classify_task()]
        )

    @task
    def pdf_error_logging_task(self) -> Task:
        return Task(
            config=self.tasks_config['pdf_error_logging_task'],
            agent=self.pdf_processor_agent(),
            context=[self.pdf_text_extraction_task()]
        )

    @task
    def entity_extraction_formatting_task(self) -> Task:
        return Task(
            config=self.tasks_config['entity_extraction_formatting_task'],
            agent=self.entity_formatter_agent(),
            context=[self.pdf_text_extraction_task()],
            output_file="output/candidate_data.json"
        )

    @task
    def entity_validation_reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config['entity_validation_reporting_task'],
            agent=self.entity_formatter_agent(),
            context=[self.entity_extraction_formatting_task()],
            output_file="output/error_entity_report.md"
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.file_validator_agent(),
                self.pdf_processor_agent(),
                self.entity_formatter_agent()
            ],
            tasks=[
                self.validate_and_classify_task(),
                self.error_reporting_task(),
                self.pdf_text_extraction_task(),
                self.pdf_error_logging_task(),
                self.entity_extraction_formatting_task(),
                self.entity_validation_reporting_task()
            ],
            process=Process.sequential,
            verbose=True
        )

    def test_crew(self, file_path: str = None):
        """Enhanced test function with better error handling and rate limit management"""
        if file_path is None:
            file_path = "D:/advansys/CVsdirectory/mohyyy.pdf"
        
        print("\n" + "=" * 50)
        print("TESTING CREW EXECUTION")
        print("=" * 50)
        
        try:
            print("Starting crew execution...")
            
            # Add rate limit handling
            import time
            time.sleep(2)  # Brief pause to avoid immediate rate limits
            
            result = self.crew().kickoff(
                inputs={"file_path": file_path}
            )
            
            print(f"Crew execution completed successfully!")
            print(f"Final Result: {result}")
            
            return result
                
        except Exception as e:
            print(f"Error during crew testing: {str(e)}")
            
            # Better error categorization
            if "rate_limit" in str(e).lower():
                print("Rate limit reached. Consider:")
                print("1. Using a different LLM provider")
                print("2. Adding delays between requests")
                print("3. Upgrading your API tier")
            elif "timeout" in str(e).lower():
                print("Task timeout. Consider increasing max_execution_time")
            
            import traceback
            traceback.print_exc()
            return None


def main():
    """Main function to run the CV processing crew."""
    # Test file paths
    test_files = [
        "C:\\Users\\abdal\\Desktop\\InternProject\\talentcopilot\\Abdallah.pdf"
    ]
    
    # Check file existence
    for file_path in test_files:
        print(f"File exists: {file_path} - {os.path.exists(file_path)}")
        if os.path.exists(file_path):
            print(f"File readable: {file_path} - {os.access(file_path, os.R_OK)}")
    
    # Initialize and run the crew
    try:
        cv_crew = CVProcessingCrew()
        
        # Use the first available test file
        test_file = None
        for file_path in test_files:
            if os.path.exists(file_path):
                test_file = file_path
                break
        
        if test_file:
            print(f"Using test file: {test_file}")
            result = cv_crew.test_crew(test_file)
        else:
            print("No test files found. Please update the file paths in the main function.")
            
    except Exception as e:
        print(f"Error initializing CV Processing Crew: {str(e)}")
        import traceback
        traceback.print_exc()


# if __name_ == "_main_":
#     main()