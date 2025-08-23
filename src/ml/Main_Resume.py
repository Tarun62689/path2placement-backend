import re
import os
import sys
import json
import tempfile
import PyPDF2
import docx
import spacy
import nltk
from supabase import create_client, Client

# --- Supabase Credentials from ENV ---
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# --- Setup ---
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None

# --- Init Supabase client ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Fetch Job Roles ---
def fetch_job_roles_from_supabase():
    response = supabase.table('job_roles').select(
        'role_name, skills, course_recommendations'
    ).execute()

    job_roles_data = {}
    for item in response.data:
        role_name = item.get('role_name')
        skills = item.get('skills', [])
        courses = item.get('course_recommendations', [])
        if role_name and skills:
            job_roles_data[role_name] = {
                "all_skills": skills,
                "recommendations": {s: c for s, c in zip(skills, courses)}
            }
    return job_roles_data

# --- Download file from Supabase ---
def download_resume_from_supabase(storage_path: str) -> str:
    """
    Download resume from Supabase storage (bucket: Resume_files).
    Returns a local temp file path.
    """
    try:
        response = supabase.storage.from_("Resume_files").download(storage_path)
        if not response:
            raise Exception(f"File '{storage_path}' not found in Supabase storage")

        # Save to temporary file
        _, ext = os.path.splitext(storage_path)
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp_file.write(response)
        tmp_file.close()
        return tmp_file.name
    except Exception as e:
        raise Exception(f"Failed to download file: {e}")

# --- File Extractors ---
def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_text_from_docx(docx_path):
    text = ""
    document = docx.Document(docx_path)
    for para in document.paragraphs:
        text += para.text + "\n"
    return text

def extract_text_from_file(file_path):
    _, ext = os.path.splitext(file_path)
    if ext.lower() == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext.lower() == ".docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file type. Use PDF or DOCX.")

# --- Analysis Functions ---
def extract_skills(text, job_role, job_roles_data):
    skills_found = set()
    text_lower = text.lower()
    all_skills = job_roles_data[job_role]["all_skills"]

    for skill in all_skills:
        if re.search(r'\b' + re.escape(skill.lower()) + r'\b', text_lower):
            skills_found.add(skill)
    return sorted(list(skills_found))

def calculate_score(skills_found, job_role, job_roles_data):
    all_skills = set(job_roles_data[job_role]["all_skills"])
    found = set(skills_found)
    matches = len(found.intersection(all_skills))
    total = len(all_skills)
    score = round((matches / total) * 100, 1) if total > 0 else 0
    return score, matches, total

def identify_skill_gaps(skills_found, job_role, job_roles_data):
    all_skills = set(job_roles_data[job_role]["all_skills"])
    return sorted(list(all_skills - set(skills_found)))

def recommend_courses(skill_gaps, job_role, job_roles_data):
    rec_map = job_roles_data[job_role]['recommendations']
    return [{"skill": s, "course": rec_map.get(s)} for s in skill_gaps if rec_map.get(s)]

def analyze_resume(text, job_role, job_roles_data):
    skills_found = extract_skills(text, job_role, job_roles_data)
    score, matches, total = calculate_score(skills_found, job_role, job_roles_data)
    skill_gaps = identify_skill_gaps(skills_found, job_role, job_roles_data)
    courses = recommend_courses(skill_gaps, job_role, job_roles_data)

    return {
        "job_role": job_role.replace("_", " ").title(),
        "score": score,
        "skills_found": skills_found,
        "skill_gaps": skill_gaps,
        "course_recommendations": courses,
        "skill_stats": {"matches": matches, "total_skills": total}
    }

# --- Main Execution ---
def main():
    try:
        job_roles_data = fetch_job_roles_from_supabase()
    except Exception as e:
        print(f"Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)

    # --- API Mode: read JSON from stdin ---
    if not sys.argv[1:]:
        try:
            input_data = json.load(sys.stdin)
            resume_path = input_data["resume_path"]   # e.g. "12345/resume.pdf"
            job_role = input_data["job_role"]
        except Exception as e:
            print(f"Invalid input JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if len(sys.argv) < 3:
            print("Usage: python Main_Resume.py <resume_path> <job_role>", file=sys.stderr)
            sys.exit(1)
        resume_path = sys.argv[1]
        job_role = sys.argv[2]

    if job_role not in job_roles_data:
        print(f"Job role '{job_role}' not found in database", file=sys.stderr)
        sys.exit(1)

    try:
        # ✅ Download file from Supabase
        local_file = download_resume_from_supabase(resume_path)

        resume_text = extract_text_from_file(local_file)
        result = analyze_resume(resume_text, job_role, job_roles_data)

        print(json.dumps(result))   # ✅ Only result to stdout

        os.remove(local_file)  # cleanup temp file
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
