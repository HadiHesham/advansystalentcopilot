#!/usr/bin/env python
import os
from crewai.flow.flow import Flow, listen, start
from .first_crew_test import CVProcessingCrew
from .extract_crew import ExtractCrew
from .crew import Talentcopilot

# Define the flow
class CVProcessingFlow:
    def __init__(self):
        # Initialize the crews
        self.cv_processing_crew = CVProcessingCrew().crew()
        # self.extract_crew = ExtractCrew().crew()
        self.talentcopilot_crew = Talentcopilot().crew()

    def run(self, pdf_file_path: str):
        """
        Run the flow:
        1. Process the PDF file to extract text and convert it into JSON.
        2. Use the ExtractCrew to convert JSON into a structured format.
        3. Use the Talentcopilot crew to insert the structured data into the database.
        """
        print("\n" + "=" * 50)
        print("STEP 1: Processing PDF with CV Processing Crew")
        print("=" * 50)
        cv_result = self.cv_processing_crew.kickoff(inputs={"file_path": pdf_file_path})
        print("CV Processing Crew Result:", cv_result)

        # Extract the JSON output from the CV Processing Crew
        json_output_path = "output/candidate_data.json"  # Ensure this matches the output file path in your tasks
        if not os.path.exists(json_output_path):
            raise FileNotFoundError(f"JSON output file not found at {json_output_path}")

        print("\n" + "=" * 50)
        print("STEP 2: Extracting Structured Data with Extract Crew")
        print("=" * 50)
        extract_result = self.extract_crew.kickoff(inputs={"json_file_path": json_output_path})
        print("Extract Crew Result:", extract_result)

        # Extract the structured data output from the Extract Crew
        structured_data_path = "output/structured_candidate_data.json"  # Ensure this matches the output file path in your tasks
        if not os.path.exists(structured_data_path):
            raise FileNotFoundError(f"Structured data file not found at {structured_data_path}")

        print("\n" + "=" * 50)
        print("STEP 3: Inserting Data into Database with Talentcopilot Crew")
        print("=" * 50)
        db_result = self.talentcopilot_crew.kickoff(inputs={"structured_data_path": structured_data_path})
        print("Talentcopilot Crew Result:", db_result)

        print("\n" + "=" * 50)
        print("FLOW COMPLETED SUCCESSFULLY")
        print("=" * 50)


if __name__ == "__main__":
    # Path to the input PDF file
    pdf_file_path = "C://Users//abdal//Desktop//InternProject//talentcopilot//Abdallah.pdf"  # Replace with the actual path to your PDF file

    # Check if the file exists
    if not os.path.exists(pdf_file_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_file_path}")

    # Run the flow
    flow = CVProcessingFlow()
    flow.run(pdf_file_path)