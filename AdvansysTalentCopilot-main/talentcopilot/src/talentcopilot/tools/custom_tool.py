from crewai.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field
import json
import uuid
from pathlib import Path

class CandidateJSONParserToolInput(BaseModel):
    json_path: str = Field(
        default="src/talentcopilot/output/candidate_data.json",
        description="Path to the input JSON file."
    )

class CandidateJSONParserTool(BaseTool):
    name: str = "Candidate JSON Parser Tool"
    description: str = (
        "Parses a JSON file of candidate data and returns structured dictionaries per table for further processing."
    )
    args_schema: Type[BaseModel] = CandidateJSONParserToolInput

    def _ensure_list(self, x):
        if x is None:
            return []
        if isinstance(x, list):
            return x
        return [x]

    def _safe(self, value):
        return value if value is not None else ""

    def _run(self, json_path: str = "src/talentcopilot/output/candidate_data.json") -> List[dict]:
        if not Path(json_path).exists():
            return [{"error": f"File '{json_path}' does not exist."}]
    
        with open(json_path, "r") as file:
            entry = json.load(file)

        outputs = []
        candidate_id = str(uuid.uuid4())

        # Candidate
        candidate = entry.get("candidate", {})
        outputs.append({
            "table": "Candidates",
            "values": {
                "id": candidate_id,
                "FirstName": self._safe(candidate.get("FirstName")),
                "LastName": self._safe(candidate.get("LastName")),
                "email": self._safe(candidate.get("email")),
                "PhoneNumber": self._safe(candidate.get("PhoneNumber")),
                "LinkedInURL": self._safe(candidate.get("LinkedInURL")),
                "GithubURL": self._safe(candidate.get("GithubURL")),
                "Address": self._safe(candidate.get("Address")),
                "status": self._safe(candidate.get("Status")),
            }
        })

        # Skills
        for skill in self._ensure_list(entry.get("skills")):
            skill["candidateId"] = candidate_id
            outputs.append({
                "table": "Skills",
                "values": skill
            })

        # Experience
        for exp in self._ensure_list(entry.get("experience")):
            exp["candidateId"] = candidate_id
            outputs.append({
                "table": "Experience",
                "values": exp
            })

        # Projects
        for proj in self._ensure_list(entry.get("projects")):
            proj["candidateId"] = candidate_id
            outputs.append({
                "table": "Projects",
                "values": proj
            })

        # Extracurricular
        for extra in self._ensure_list(entry.get("extracurricular")):
            extra["candidateId"] = candidate_id
            outputs.append({
                "table": "ExtraCurriculum",
                "values": extra
            })

        return outputs

if __name__ == "__main__":
    tool = CandidateJSONParserTool()
    result = tool._run()
    print(result)