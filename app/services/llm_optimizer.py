import os
import json
from typing import List, Tuple, Dict, Any
from groq import Groq
from app.models.schemas import JDKeywords, StructuredResume, CoverLetter
from app.utils.text_cleaner import clean_text, clean_keywords


def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing. Please set it to use the AI services.")
    return Groq(api_key=api_key)

def extract_jd_keywords(jd_text: str) -> JDKeywords:
    client = get_groq_client()
    prompt = f"""
    You are an expert ATS (Applicant Tracking System) parser.
    Extract the following from the Job Description provided below:
    - job_title: The specific job title being hired for.
    - hard_skills: BE EXHAUSTIVE. Extract every technical skill, software, tool, programming language, methodology (Agile, Scrum, etc.), and industry-specific terminology mentioned.
    - soft_skills: Interpersonal skills, traits (e.g. leadership, communication).
    - action_verbs: Key verbs used to describe responsibilities (e.g. managed, developed, pioneered).
    - certifications: Required or preferred certifications or degrees.

    
    Output strictly as valid JSON matching this schema exactly:
    {{
        "job_title": "...",
        "hard_skills": ["..."],
        "soft_skills": ["..."],
        "action_verbs": ["..."],
        "certifications": ["..."]
    }}
    
    Job Description:
    {jd_text}
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    content = response.choices[0].message.content
    if not content:
         raise ValueError("Empty response from Groq")
    
    obj = JDKeywords.model_validate_json(content)
    # Clean the keywords
    obj.hard_skills = clean_keywords(obj.hard_skills)
    obj.soft_skills = clean_keywords(obj.soft_skills)
    obj.action_verbs = clean_keywords(obj.action_verbs)
    obj.certifications = clean_keywords(obj.certifications)
    obj.job_title = obj.job_title.strip()
    return obj


def optimize_resume(resume_text: str, jd_keywords: JDKeywords, feedback: str = "", target_ats: str = "all", force_quantify: bool = False) -> StructuredResume:
    client = get_groq_client()
    
    # Impact-specific rule
    quantify_rule = ""
    if force_quantify:
        quantify_rule = """
        MANDATORY: FORCE QUANTIFIED ACHIEVEMENTS.
        - EVERY SINGLE bullet point in the 'Professional Experience' section MUST include at least one number, percentage, or dollar amount.
        - If the original text is vague (e.g., 'Responsible for sales'), you MUST rewrite it to show measurable impact (e.g., 'Increased sales revenue by 12% through targeted lead generation').
        - Use industry-standard benchmarks if specific numbers aren't provided, but ensure they are realistic based on the role.
        - FAILURE TO INCLUDE A NUMBER IN EVERY BULLET IS UNACCEPTABLE.
        """

    
    # System-specific rules
    ats_rules = {
        "taleo": "SPECIAL FOCUS: Oracle Taleo is extremely strict. Use standard section headers ONLY. Avoid all special characters. Ensure the 'Skills' section is comma-separated and uses exact JD terminology.",
        "workday": "SPECIAL FOCUS: Workday prefers chronological order and is sensitive to date formatting. Ensure dates are clearly separated. Use 'Professional Experience' as the main header.",
        "greenhouse": "SPECIAL FOCUS: Greenhouse is more modern but values the STAR method above all else. Ensure every bullet has a metric.",
        "icims": "SPECIAL FOCUS: iCIMS parsers prioritize the 'Summary' section for keyword density. Front-load your most important skills there.",
        "lever": "SPECIAL FOCUS: Lever uses semantic indexing. Use synonyms for key skills naturally throughout the text.",
        "all": "SPECIAL FOCUS: Optimization for universal compatibility. Use the most conservative and widely accepted formatting and keyword strategies."
    }

    target_rule = ats_rules.get(target_ats.lower(), ats_rules["all"])

    system_prompt = f"""
    You are a World-Class Executive Resume Writer and ATS Architect. 
    Your goal is to generate a resume that achieves a 95%+ match score on {target_ats.upper()} and high-end checkers like EnhanceCV.

    {target_rule}
    {quantify_rule}

    CRITICAL RULES FOR PERFECTION:
    1. STAR METHOD & QUANTIFICATION (BRUTAL ENFORCEMENT): 
       - EVERY SINGLE bullet point in the 'experience' section MUST follow the STAR framework (Situation, Task, Action, Result). 
       - EVERY bullet MUST include a QUANTIFIED RESULT (%, $, numbers, or scale). 
       - Avoid vague phrases; use measurable achievements (e.g., "Improved process, resulting in a 20% reduction in lead time").
    
    2. STRATEGIC KEYWORD INTEGRATION: 
       - EXACT MATCH: Use the EXACT terminology from the Job Description for Hard Skills. 
       - DUAL-EXPOSURE: Include keywords in both 'SKILLS' and 'EXPERIENCE' sections.

    3. VOCABULARY DIVERSITY & ZERO-REPETITION POLICY: 
       - ABSOLUTE LIMIT: No action verb (e.g., "Spearheaded", "Conducted", "Led", "Applied") may appear more than ONCE in the entire document.
       - BULLET STARTERS: Every bullet point MUST start with a unique action verb. NEVER start two bullets with the same word.
       - SYNONYM OVERLOAD: If you used 'Conducted' once, use 'Performed' or 'Executed'. If you used 'Applied', use 'Utilized', 'Implemented', or 'Deployed'.

    4. PROOFREADING & GRAMMAR PRECISION: 
       - VERB TENSE: Use PAST TENSE for previous roles and PRESENT TENSE only for the current/active role. 
       - PUNCTUATION: Every bullet point MUST end with a period (.).
       - SPELLING: Use 100% American English (e.g., 'Optimized' not 'Optimised').
       - VOICE: Use ACTIVE VOICE only. No "Responsible for".

    5. STANDARDIZED HEADERS: Use "SUMMARY", "WORK EXPERIENCE", "EDUCATION", "SKILLS", "CERTIFICATIONS".
    6. DATE CONSISTENCY: Format all dates as 'Month YYYY - Month YYYY'.
    """

    if feedback:
        system_prompt += f"\n\nFEEDBACK FROM PREVIOUS ITERATION TO IMPROVE ON:\n{feedback}\nPlease ensure these missing keywords are integrated naturally."
    
    user_prompt = f"""
    Target Keywords to Inject naturally:
    {jd_keywords.model_dump_json()}
    
    Original Resume Text:
    {resume_text}
    
    Output as valid JSON matching this exact schema:
    {{
      "contact_info": {{"name": "...", "email": "...", "phone": "...", "location": "...", "linkedin": "...", "website": "..."}},
      "summary": "...",
      "experience": [{{"title": "...", "company": "...", "start_date": "...", "end_date": "...", "location": "...", "bullet_points": ["..."]}}],
      "education": [{{"degree": "...", "institution": "...", "graduation_date": "...", "location": "..."}}],
      "skills": ["..."],
      "certifications": ["..."]
    }}
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    
    content = response.choices[0].message.content
    if not content:
         raise ValueError("Empty response from Groq")
    
    resume = StructuredResume.model_validate_json(content)
    
    # Clean the resume text fields
    resume.summary = clean_text(resume.summary)
    for exp in resume.experience:
        exp.title = exp.title.strip()
        exp.company = exp.company.strip()
        exp.bullet_points = [clean_text(bp) for bp in exp.bullet_points]
    
    resume.skills = clean_keywords(resume.skills)
    resume.certifications = clean_keywords(resume.certifications)

    # ── Post-processing: deduplicate repeated action verbs ──────────────────
    # Build a synonym map: overused word → list of alternatives
    VERB_SYNONYMS = {
        "applied":      ["Utilized", "Implemented", "Deployed", "Leveraged", "Exercised"],
        "conducted":    ["Performed", "Executed", "Spearheaded", "Facilitated", "Orchestrated"],
        "managed":      ["Oversaw", "Directed", "Steered", "Supervised", "Governed"],
        "developed":    ["Engineered", "Architected", "Built", "Crafted", "Established"],
        "improved":     ["Enhanced", "Optimized", "Elevated", "Accelerated", "Refined"],
        "led":          ["Spearheaded", "Championed", "Drove", "Pioneered", "Headed"],
        "created":      ["Designed", "Produced", "Formulated", "Instituted", "Launched"],
        "supported":    ["Assisted", "Reinforced", "Bolstered", "Aided", "Facilitated"],
        "ensured":      ["Validated", "Verified", "Guaranteed", "Secured", "Confirmed"],
        "utilized":     ["Applied", "Harnessed", "Employed", "Leveraged", "Deployed"],
        "assisted":     ["Supported", "Contributed", "Collaborated", "Enabled", "Aided"],
    }

    used_starts: dict = {}   # word_lower → count of uses as bullet starter
    import re as _re
    for exp in resume.experience:
        new_bullets = []
        for bp in exp.bullet_points:
            first_word_match = _re.match(r'^([A-Za-z]+)', bp.strip())
            if first_word_match:
                first_word = first_word_match.group(1).lower()
                used_starts[first_word] = used_starts.get(first_word, 0) + 1
                # If this word has been used before AND we have a synonym, replace it
                if used_starts[first_word] > 1 and first_word in VERB_SYNONYMS:
                    synonym_list = VERB_SYNONYMS[first_word]
                    # Pick synonym based on how many times we've already replaced
                    replacement = synonym_list[min(used_starts[first_word] - 2, len(synonym_list) - 1)]
                    bp = _re.sub(r'^[A-Za-z]+', replacement, bp.strip(), count=1)
            new_bullets.append(bp)
        exp.bullet_points = new_bullets
    # ────────────────────────────────────────────────────────────────────────

    return resume


def select_template(jd_text: str) -> str:
    client = get_groq_client()
    prompt = f"""
    Classify the following Job Description into one of these 5 template categories based on the industry and role:
    - tech
    - finance
    - healthcare
    - executive
    - general
    
    Respond with ONLY the exact category name in lowercase. No other text.
    
    JD:
    {jd_text}
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    category = response.choices[0].message.content
    if not category:
         return "general"
    category = category.strip().lower()
    valid_categories = ["tech", "finance", "healthcare", "executive", "general"]
    if category not in valid_categories:
        return "general"
    return category

def calculate_ats_score(optimized_resume: StructuredResume, jd_keywords: JDKeywords, force_quantify: bool = False) -> Tuple[float, str]:

    import re
    resume_json = optimized_resume.model_dump_json().lower()
    summary = optimized_resume.summary.lower()
    
    # 1. Weights (Industry Standard)
    weights = {
        "job_title": 0.25,      # 25% for matching the target role
        "hard_skills": 0.45,    # 45% for technical proficiency
        "soft_skills": 0.15,    # 15% for soft skills
        "action_verbs": 0.05,   # 5% for professional language
        "impact": 0.10          # 10% for quantification (%, $, numbers)
    }
    
    final_score = 0.0
    missing_critical = []

    # Helper: Whole-word search with density check
    def keyword_analysis(keywords: List[str], text: str) -> Tuple[float, List[str]]:
        if not keywords: return 100.0, []
        found_count = 0
        missing = []
        for kw in keywords:
            if not kw.strip(): continue
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            matches = len(re.findall(pattern, text))
            if matches > 0:
                # Density Bonus: Real ATS likes seeing key skills 2-3 times
                score_increment = 1.0 if matches >= 2 else 0.8
                found_count += score_increment
            else:
                missing.append(kw)
        return (min(1.0, found_count / len(keywords)) * 100), missing

    # A. Job Title Match (25%)
    # Checks if the target title is in the Summary or the most recent Job Title
    title_pattern = r'\b' + re.escape(jd_keywords.job_title.lower()) + r'\b'
    recent_job = optimized_resume.experience[0].title.lower() if optimized_resume.experience else ""
    if re.search(title_pattern, summary) or re.search(title_pattern, recent_job):
        final_score += (weights["job_title"] * 100)
    else:
        # Partial credit for word-by-word match
        title_words = jd_keywords.job_title.lower().split()
        title_matches = sum(1 for w in title_words if w in summary or w in recent_job)
        if title_words:
            final_score += (weights["job_title"] * (title_matches / len(title_words)) * 50)
        missing_critical.append(f"Target Title: {jd_keywords.job_title}")

    # B. Hard Skills (45%)
    # Use context weighting: Hard skills in the 'skills' section are good, 
    # but skills in 'experience' bullets are worth significantly more for systems like Jobscan.
    hard_skills_all = jd_keywords.hard_skills + jd_keywords.certifications
    h_total = len(hard_skills_all)
    if h_total > 0:
        found_in_list = 0
        found_in_experience = 0
        
        exp_text = " ".join([bp for exp in optimized_resume.experience for bp in exp.bullet_points]).lower()
        
        for kw in hard_skills_all:
            if not kw.strip(): continue
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            
            in_resume = re.search(pattern, resume_json)
            in_exp = re.search(pattern, exp_text)
            
            if in_resume: found_in_list += 1
            if in_exp: found_in_experience += 1
            else: missing_critical.append(f"Skill missing context: {kw} (add to experience)")
            
        # Hard score is average of presence and context
        presence_score = (found_in_list / h_total) * 100
        context_score = (found_in_experience / h_total) * 100
        hard_score = (presence_score * 0.4) + (context_score * 0.6)
        
        final_score += (weights["hard_skills"] * hard_score)
        if h_total > found_in_list:
            missing_critical.extend([kw for kw in hard_skills_all if not re.search(r'\b' + re.escape(kw.lower()) + r'\b', resume_json)][:5])
    else:
        final_score += (weights["hard_skills"] * 100)


    # C. Soft Skills (15%)
    soft_score, _ = keyword_analysis(jd_keywords.soft_skills, resume_json)
    final_score += (weights["soft_skills"] * soft_score)

    # D. Action Verbs (5%)
    verb_score, _ = keyword_analysis(jd_keywords.action_verbs, resume_json)
    final_score += (weights["action_verbs"] * verb_score)

    # E. Impact Density (10%)
    # Counts how many bullets contain numbers/metrics
    total_bullets = 0
    bullets_with_metrics = 0
    for exp in optimized_resume.experience:
        for bullet in exp.bullet_points:
            total_bullets += 1
            if re.search(r'\d+|%|\$', bullet):
                bullets_with_metrics += 1
    
    if total_bullets > 0:
        metric_ratio = bullets_with_metrics / total_bullets
        
        if force_quantify:
            # If forced, we expect 100% density. Penalty if less.
            impact_score = metric_ratio * 100
            if metric_ratio < 1.0:
                missing_critical.append(f"MANDATORY QUANTIFICATION MISSING: {total_bullets - bullets_with_metrics} bullet points are still missing metrics (%, $, numbers) despite 'Force Quantify' being enabled.")
        else:
            # Ideal ratio is > 60% for standard resumes
            impact_score = min(1.0, metric_ratio / 0.6) * 100
            
        final_score += (weights["impact"] * impact_score)


    # F. Structural & Vocabulary Penalties
    # 1. Penalty for missing sections or short summary
    if not optimized_resume.summary or len(optimized_resume.summary.split()) < 20:
        final_score -= 5
    if len(optimized_resume.experience) < 2:
        final_score -= 5

    # 2. Vocabulary Repetition Penalty
    # Track common action verbs and keywords
    all_text = (
        optimized_resume.summary + " " + 
        " ".join([bp for exp in optimized_resume.experience for bp in exp.bullet_points]) + " " +
        " ".join(optimized_resume.skills) + " " +
        " ".join(optimized_resume.certifications or [])
    ).lower()

    common_words = [
        "managed", "led", "conducted", "applied", "utilized", "certified", "responsible", "handled", 
        "oversaw", "worked", "experienced", "passionate", "team player", 
        "dynamic", "hardworking", "results-oriented", "skilled", "expert"
    ]

    repetition_found = []
    for word in common_words:
        count = len(re.findall(r'\b' + re.escape(word) + r'\b', all_text))
        if count > 1:
            final_score -= (count * 5)
            repetition_found.append(f"{word} ({count}x)")
    
    if repetition_found:
        missing_critical.append(f"REPETITION DETECTED: {', '.join(repetition_found)} are repeated. Replace with synonyms.")


    # 3. Punctuation & Consistency Penalty
    # Check if bullet points end with periods
    missing_periods = 0
    total_bp = 0
    for exp in optimized_resume.experience:
        for bp in exp.bullet_points:
            total_bp += 1
            if bp and not bp.strip().endswith('.'):
                missing_periods += 1
    
    if missing_periods > 0:
        final_score -= (missing_periods * 1)
        missing_critical.append(f"PUNCTUATION ERROR: {missing_periods} bullet points are missing ending periods. Every bullet must end with a period for consistency.")

    final_score = min(100.0, max(0.0, final_score))


    
    feedback = ""
    if missing_critical:
        feedback = "Critical gaps identified: " + ", ".join(missing_critical[:8])
            
    return round(final_score, 2), feedback

def generate_cover_letter(resume: StructuredResume, jd_text: str, target_ats: str = "all", target_company: str = "") -> CoverLetter:
    client = get_groq_client()
    
    company_name_hint = target_company if target_company else "the company mentioned in the job description"

    prompt = f"""
    You are a World-Class Executive Career Coach. 
    Write a high-impact, ATS-optimized Cover Letter for the following candidate.

    TARGET COMPANY: {company_name_hint}
    
    CANDIDATE DATA:
    {resume.model_dump_json()}

    JOB DESCRIPTION:
    {jd_text}

    CRITICAL RULES FOR ACCURACY:
    1. EMPLOYER DISCRIMINATION: Do NOT address the letter to any company listed in the candidate's 'experience' section (e.g., YKK). The recipient is ONLY {company_name_hint}.
    2. THE BRIDGE STRATEGY: 
       - Identify the top 2-3 most relevant experiences from the candidate's resume that match the job requirements.
       - Explicitly explain HOW those specific skills (e.g., from their time at YKK) make them the perfect fit for {company_name_hint}.
    3. NO REDUNDANCY: Do NOT include 'Dear Hiring Manager' or 'Sincerely' inside the 'content' field. The 'content' field should ONLY contain the body paragraphs.
    4. TONE: Professional, confident, and achievement-oriented.
    5. KEYWORDS: Naturally include top keywords from the Job Description.
    6. LENGTH: 250-400 words.

    Output strictly as valid JSON matching this schema:
    {{
        "date": "Today's Date",
        "recipient_name": "Hiring Manager",
        "company_name": "{company_name_hint}",
        "content": "Full body text...",
        "salutation": "Dear",
        "closing": "Sincerely"
    }}
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a professional career coach. Output JSON only."},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" }
    )
    
    content = response.choices[0].message.content
    cl = CoverLetter.model_validate_json(content)
    cl.content = clean_text(cl.content)
    return cl


def parse_resume(raw_text: str) -> StructuredResume:
    """Parses raw resume text into the StructuredResume schema for scoring."""
    client = get_groq_client()
    prompt = f"""
    Extract the following information from the raw resume text into a structured JSON format.
    
    RAW TEXT:
    {raw_text}
    
    SCHEMA:
    {StructuredResume.model_json_schema()}
    
    Output strictly as valid JSON.
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a professional resume parser. Output JSON only."},
            {"role": "user", "content": prompt}
        ],
        response_format={ "type": "json_object" }
    )
    return StructuredResume.model_validate_json(response.choices[0].message.content)

def calculate_ats_score_raw(raw_text: str, jd_keywords: JDKeywords) -> float:
    """Calculates an ATS score for raw text (useful for the 'Before' comparison)."""
    import re
    text = raw_text.lower()
    
    weights = {
        "job_title": 0.25,
        "hard_skills": 0.45,
        "soft_skills": 0.15,
        "action_verbs": 0.05,
        "impact": 0.10
    }
    
    score = 0.0
    
    # 1. Job Title (Simple check)
    if re.search(r'\b' + re.escape(jd_keywords.job_title.lower()) + r'\b', text):
        score += (weights["job_title"] * 100)
    
    # 2. Hard Skills
    h_found = 0
    h_total = len(jd_keywords.hard_skills)
    if h_total > 0:
        for kw in jd_keywords.hard_skills:
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text):
                h_found += 1
        score += (weights["hard_skills"] * (h_found / h_total) * 100)
    else:
        score += (weights["hard_skills"] * 100)

    # 3. Soft Skills & Verbs
    all_others = jd_keywords.soft_skills + jd_keywords.action_verbs
    o_found = 0
    if all_others:
        for kw in all_others:
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text):
                o_found += 1
        score += ((weights["soft_skills"] + weights["action_verbs"]) * (o_found / len(all_others)) * 100)
    
    # 4. Impact (Numbers check)
    metrics = len(re.findall(r'\d+|%|\$', text))
    if metrics > 5: score += (weights["impact"] * 100)
    elif metrics > 0: score += (weights["impact"] * 50)

    return round(min(100.0, score), 2)
