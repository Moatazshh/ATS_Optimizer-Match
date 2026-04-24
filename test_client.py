import requests
import os

def test_optimization():
    url = "http://localhost:8000/api/v1/optimize"
    
    # --- CONFIGURATION ---
    # 1. Path to a local PDF or DOCX resume
    resume_path = input("Enter the full path to your resume file (PDF or DOCX): ").strip().strip('"')
    
    # 2. Sample Job Description
    jd_text = """
    We are looking for a Senior Software Engineer with 5+ years of experience in Python.
    Key skills: FastAPI, AWS, Docker, and PostgreSQL. 
    The ideal candidate should have experience leading teams and delivering scalable microservices.
    """
    
    if not os.path.exists(resume_path):
        print(f"Error: File not found at {resume_path}")
        return

    print(f"Optimizing {os.path.basename(resume_path)}...")

    try:
        with open(resume_path, "rb") as f:
            files = {"resume_file": (os.path.basename(resume_path), f)}
            data = {"jd_text": jd_text}
            
            response = requests.post(url, files=files, data=data)
            
        if response.status_code == 200:
            output_file = "optimized_resume.docx"
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            print("--- Success! ---")
            print(f"ATS Score: {response.headers.get('X-ATS-Score')}%")
            print(f"Iterations: {response.headers.get('X-Iterations')}")
            print(f"Template: {response.headers.get('X-Template-Used')}")
            print(f"Saved to: {os.path.abspath(output_file)}")
        else:
            print(f"Failed with status {response.status_code}")
            print(response.json())
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_optimization()
