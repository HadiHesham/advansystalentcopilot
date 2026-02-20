# mysql_tool.py

import mysql.connector
import json

def extract_candidate_data_from_mysql(db_config, output_path="collected_skills.json"):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # Get candidate info
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

    # Skills
    cursor.execute("SELECT candidate_id, name, type FROM skills")
    for row in cursor.fetchall():
        cid = row['candidate_id']
        if row['type'] == 'technical':
            candidates[cid]['technical_skills'].append(row['name'])
        elif row['type'] == 'softskill':
            candidates[cid]['soft_skills'].append(row['name'])

    # Experience
    cursor.execute("SELECT candidate_id, title, company_name, start_date, end_date, description FROM experience")
    for row in cursor.fetchall():
        cid = row['candidate_id']
        desc = f"{row['title']} at {row['company_name']} ({row['start_date']} to {row['end_date'] or 'present'}): {row['description']}"
        candidates[cid]['experience'].append(desc)

    # Projects
    cursor.execute("SELECT candidate_id, project_name, title, start_date, end_date, description FROM projects")
    for row in cursor.fetchall():
        cid = row['candidate_id']
        desc = f"{row['project_name']} – {row['title']} ({row['start_date']} to {row['end_date'] or 'present'}): {row['description']}"
        candidates[cid]['projects'].append(desc)

    # Dump to JSON
    result = list(candidates.values())
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    cursor.close()
    conn.close()
    return result
