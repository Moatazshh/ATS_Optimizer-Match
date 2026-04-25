from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, HTMLResponse
import io
import os
import zipfile
from pathlib import Path
from dotenv import load_dotenv

from app.services.parser import extract_text_from_file
from app.utils.text_cleaner import clean_text
from app.services.optimizer_v2 import (

    extract_jd_keywords, 
    optimize_resume, 
    select_template, 
    calculate_ats_score,
    calculate_ats_score_raw,
    generate_cover_letter,
    parse_resume
)
from app.services.template_engine import (
    generate_docx, 
    generate_pdf, 
    generate_cover_letter_docx, 
    generate_cover_letter_pdf
)
from app.models.schemas import OptimizationResponse

load_dotenv()

app = FastAPI(title="ATS Optimizer API", version="1.0.0")

# Mount static files for the UI
app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = BASE_DIR / "static" / "index.html"
    return index_path.read_text(encoding="utf-8")

@app.get("/policy", response_class=HTMLResponse)
async def policy():
    policy_path = BASE_DIR / "static" / "policy.html"
    return policy_path.read_text(encoding="utf-8")

@app.post("/api/v1/optimize")
async def optimize(
    resume_file: UploadFile = File(...),
    jd_text: str = Form(...),
    output_format: str = Form("docx"), # "docx" or "pdf"
    ats_system: str = Form("all"),
    target_company: str = Form(""),
    force_quantify: bool = Form(False),
    gen_cover_letter: bool = Form(False)
):
    try:
        # 1. Parse Input & Clean Text
        resume_content = await resume_file.read()
        original_text = extract_text_from_file(resume_content, resume_file.filename)
        jd_text = clean_text(jd_text)

        
        # 2. Extract JD Keywords & Select Template
        jd_keywords = extract_jd_keywords(jd_text)
        template_type = select_template(jd_text)
        
        # 2b. Calculate INITIAL Match Score (Before Optimization)
        # Using RAW text scoring for a "brutally honest" assessment of the original
        initial_score = calculate_ats_score_raw(original_text, jd_keywords)
        
        # 3. Iteration Loop (Phase 4)
        current_iteration = 0
        max_iterations = 2
        best_resume = None
        best_score = -1.0
        best_feedback = ""
        
        loop_feedback = ""
        
        while current_iteration < max_iterations:
            current_iteration += 1
            
            # AI Generation
            optimized_resume = optimize_resume(original_text, jd_keywords, loop_feedback, ats_system, force_quantify)
            
            # Scoring
            score, feedback = calculate_ats_score(optimized_resume, jd_keywords, force_quantify)

            
            if score > best_score:
                best_score = score
                best_resume = optimized_resume
                best_feedback = feedback
            
            # If score is already high enough (e.g. 95+), break early
            if score >= 95.0:
                break
                
            # Otherwise, use the feedback for the next iteration
            loop_feedback = feedback

        if not best_resume:
            raise HTTPException(status_code=500, detail="Failed to generate optimized resume")

        # 4. Generate Final Documents
        if output_format.lower() == "pdf":
            resume_buffer = generate_pdf(best_resume, template_type)
            resume_ext = "pdf"
            resume_media = "application/pdf"
        else:
            resume_buffer = generate_docx(best_resume, template_type)
            resume_ext = "docx"
            resume_media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        # 5. Handle Cover Letter
        if gen_cover_letter:
            cl_data = generate_cover_letter(best_resume, jd_text, ats_system, target_company)
            user_name = best_resume.contact_info.name
            if output_format.lower() == "pdf":
                cl_buffer = generate_cover_letter_pdf(cl_data, user_name)
                cl_ext = "pdf"
            else:
                cl_buffer = generate_cover_letter_docx(cl_data, user_name)
                cl_ext = "docx"
            
            # Package into ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                zf.writestr(f"Optimized_Resume_ATS_{int(best_score)}.{resume_ext}", resume_buffer.getvalue())
                zf.writestr(f"Matching_Cover_Letter.{cl_ext}", cl_buffer.getvalue())
            
            zip_buffer.seek(0)
            headers = {
                "X-ATS-Score": str(best_score),
                "X-Initial-Score": str(initial_score),
                "X-ATS-Feedback": best_feedback,
                "Content-Disposition": f"attachment; filename=ATS_Application_Package.zip"

            }
            return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)

        # Return Single File if no cover letter
        headers = {
            "X-ATS-Score": str(best_score),
            "X-Initial-Score": str(initial_score),
            "X-ATS-Feedback": best_feedback,
            "X-Iterations": str(current_iteration),
            "X-Template-Used": template_type,
            "Content-Disposition": f"attachment; filename=Optimized_Resume_ATS_{int(best_score)}.{resume_ext}"

        }
        
        return StreamingResponse(
            resume_buffer, 
            media_type=resume_media,
            headers=headers
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
