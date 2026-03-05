import os
import json
import re
import mysql.connector
import warnings
from crewai import Agent, Task, Crew
from langchain_community.llms import Cohere

# warnings.filterwarnings("ignore")

# === Configuration ===
os.environ["COHERE_API_KEY"] = "lQKMeWNnIbTjGvhXMTgYGr7pwDvAE06xABYzHHBN"
job_description_path = "JobDesription.txt"
job_output_txt_path = "job_analysis_output.txt"
candidate_output_json_path = "collected_skills.json"
match_output_txt_path = "candidate_matches.txt"
decision_output_txt_path = "interview_decision.txt"

# === Load Job Description ===
def load_job_description(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

job_description_text = load_job_description(job_description_path)


# === LLM Setup ===
cohere_llm = Cohere(
    model="command-r-plus",
    temperature=0.7
)

# === Load Job Description ===
def load_job_description(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

job_description_text = load_job_description(job_description_path)

# === Agents ===
JobAnalyser = Agent(
    role="Job Description Analyzer",
    goal=(
        "Extract the technical skills, soft skills"
        "required for any job based on its description."
    ),
    backstory=(
        "You are an expert in analyzing job descriptions across all industries—IT, healthcare, finance, education, and more. "
        "Your task is to thoroughly review job descriptions and extract the key qualifications required for success in the role. "
        "These include:\n"
        "- Technical skills (e.g., tools, certifications, software, domain knowledge)\n"
        "- Soft skills (e.g., communication, leadership, adaptability)\n"
        "These extracted items are used by the Candidate Selector system to match candidates. "
        "Ensure each entry is clearly named, normalized, and in a format suitable for CV parsing. "
        "Here is the job description to analyze: {JobDescription}. "
        "Return your findings as a JSON object with the keys: 'technical_skills', 'soft_skills', 'experience', 'certifications', and 'projects'."
    ),
    allow_delegation=False,
    verbose=True,
    llm=cohere_llm
)


AnalyzeJob = Task(
    description=(
        "Analyze the following job description: {JobDescription}. "
        "Carefully read the entire description and extract all relevant expectations for the candidate. "
        "Start by identifying important keywords and phrases related to tools, technologies, behaviors, qualifications, responsibilities, and outcomes. "
        "Map those to standardized, CV-friendly names and group them into the following categories:\n"
        "1. 'technical_skills' – Specific tools, technologies, systems, certifications, programming languages, or domain knowledge.\n"
        "2. 'soft_skills' – Behavioral or interpersonal abilities such as teamwork, communication, or adaptability.\n"
        "Return the output as a JSON object with these five keys."
    ),
    expected_output=(
        "A .txt file in the following format:\n"
        "{\n"
        '  "technical_skills": ["Skill 1", "Skill 2", ...],\n'
        '  "soft_skills": ["Skill A", "Skill B", ...],\n'
        "}"
    ),
    agent=JobAnalyser,
    async_execution=False
)

AcceptReject = Agent(
    role="HR Recruitment Specialist",
    goal=(
        "Identify whether a candidate is accepted for the interview or rejected based on the candidate_matches.txt file."
    ),
    backstory=(
        "You are an experienced HR recruitment specialist responsible for making interview decisions based on candidate-job compatibility. "
        "You are provided with one input only: a plain text report (`candidate_matches.txt`) summarizing how well each candidate matches the job description. "
        "Based on this information alone, decide whether each candidate should be ACCEPTED for an interview or REJECTED. "
        "Output your decisions in a clear plain text format, listing each candidate's name, followed by 'ACCEPTED' or 'REJECTED', and a short explanation for your decision."
    ),
    allow_delegation=False,
    verbose=True,
    llm=cohere_llm)

MatchingAnalyser = Agent(
    role="HR Recruitment Specialist",
    goal=(
        "Identify the best-matching candidates based on how closely their skills align with job requirements."
    ),
    backstory=(
        "You are a highly skilled HR recruitment specialist with deep experience in screening candidates "
        "for technical and non-technical roles across industries. Your job is to carefully evaluate both job requirements "
        "and candidate profiles to determine the best fits. "
        "You are provided with:\n"
        "- The list of required skills for a job: {JOBSKILLS}\n"
        "- A dataset of candidate profiles, each listing their name, technical skills, soft skills, experience, and certifications: {CANDIDATESKILLS}\n"
        "Analyze how well each candidate matches the job requirements based on their skills.\n"
        "Output a plain text list of the most suitable candidates, ideally ranked from best match to least, and optionally include a brief justification."
    ),
    allow_delegation=False,
    verbose=True,
    llm=cohere_llm
)

AnalyzeMatch = Task(
    description=(
        "Evaluate the compatibility between the following job requirements and candidate profiles.\n\n"
        "- Job Requirements (Skills): {JOBSKILLS}\n"
        "- Candidate Data: {CANDIDATESKILLS}\n\n"
        "For each candidate, compare their skills to the required job skills. Identify those who match well, "
        "and rank them from highest to lowest based on match quality. Consider both exact matches and related skills.\n\n"
        "Return the result as plain text, listing the most viable candidates first, and include a brief explanation if needed."
    ),
    expected_output=(
        "A plain text (.txt) report listing the names of the top-matching candidates, optionally with brief explanations of their suitability."
    ),
    agent=MatchingAnalyser,
    async_execution=False
)

EvaluateInterviewEligibility = Task(
    description=(
        "You are provided with the text contents of a compatibility report between job requirements and candidate profiles.\n\n"
        "The report {MATCHRESULTS} summarizes how well each candidate matches the job description. "
        "Your task is to read this report carefully and, based solely on the information provided, determine for each candidate whether "
        "they should be ACCEPTED for an interview or REJECTED.\n\n"
        "Output your response in plain text using the following format for each candidate:\n\n"
        "Candidate: [Full Name]\n"
        "Decision: ACCEPTED or REJECTED\n"
        "Reason: [Brief explanation based on the report]\n"
    ),
    expected_output=(
        "A plain text (.txt) report listing candidates with interview decisions and justifications, one block per candidate."
    ),
    agent=AcceptReject
)


# === MySQL Extractor Function ===
def extract_candidate_data_from_mysql(db_config, output_path="collected_skills.json"):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # Step 1: Get basic candidate data
    cursor.execute("SELECT id, CONCAT(first_name, ' ', last_name) AS name FROM candidate")
    candidates = {
        row['id']: {
            "candidate_name": row['name'],
            "technical_skills": [],
            "soft_skills": [],
            "experience": [],
            "certifications": [],
            "projects": []
        } for row in cursor.fetchall()
    }

    # Step 2: Skills
    cursor.execute("SELECT candidate_id, name, type FROM skills")
    for row in cursor.fetchall():
        cid = row['candidate_id']
        if row['type'] == 'technical':
            candidates[cid]['technical_skills'].append(row['name'])
        elif row['type'] == 'softskill':
            candidates[cid]['soft_skills'].append(row['name'])

    # Step 3: Experience
    cursor.execute("SELECT candidate_id, title, company_name, start_date, end_date, description FROM experience")
    for row in cursor.fetchall():
        cid = row['candidate_id']
        desc = f"{row['title']} at {row['company_name']} ({row['start_date']} to {row['end_date'] or 'present'}): {row['description']}"
        candidates[cid]['experience'].append(desc)

    # Step 4: Projects
    cursor.execute("SELECT candidate_id, project_name, title, start_date, end_date, description FROM projects")
    for row in cursor.fetchall():
        cid = row['candidate_id']
        desc = f"{row['project_name']} – {row['title']} ({row['start_date']} to {row['end_date'] or 'present'}): {row['description']}"
        candidates[cid]['projects'].append(desc)

    # Step 5: Output to JSON
    result = list(candidates.values())
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    cursor.close()
    conn.close()
    return result


import os
import json
import mysql.connector
from crewai import Crew
# === Step 1: Analyze Job Description ===
print("🔍 Analyzing job description...")
job_crew = Crew(
    agents=[JobAnalyser],
    tasks=[AnalyzeJob],
    verbose=True
)
job_result = job_crew.kickoff(inputs={"JobDescription": job_description_text})

with open(job_output_txt_path, "w", encoding="utf-8") as f:
    f.write(str(job_result))

# print(f"📄 Job analysis saved to {job_output_txt_path}")


# === Step 2: Extract Candidate Data ===
print("🗃 Extracting candidate data from MySQL...")
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Dodo1977",
    "database": "intern"
}
candidate_data = extract_candidate_data_from_mysql(db_config)

# === Step 3: Match Candidates to Job ===
print("🔗 Matching candidates to job requirements...")
match_crew = Crew(
    agents=[MatchingAnalyser],
    tasks=[AnalyzeMatch],
    verbose=True
)
match_result = match_crew.kickoff(inputs={
    "JOBSKILLS": str(job_result),
    "CANDIDATESKILLS": json.dumps(candidate_data)
})

with open(match_output_txt_path, "w", encoding="utf-8") as f:
    f.write(str(match_result))

print(f"✅ Match results saved to {match_output_txt_path}")

# === Step 4: Evaluate Interview Eligibility ===
print("📋 Evaluating interview decisions...")
decision_crew = Crew(
    agents=[AcceptReject],
    tasks=[EvaluateInterviewEligibility],
    verbose=True
)
decision_result = decision_crew.kickoff(inputs={
    "MATCHRESULTS": str(match_result)
})

with open(decision_output_txt_path, "w", encoding="utf-8") as f:
    f.write(str(decision_result))

print(f"🎯 Interview decisions saved to {decision_output_txt_path}")
