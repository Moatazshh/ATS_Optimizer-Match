import re

def clean_text(text: str) -> str:
    """
    Eliminates unnecessary spaces and normalizes text.
    - Strips leading/trailing whitespace.
    - Replaces multiple spaces with a single space.
    - Normalizes line breaks (consecutive newlines to max two).
    """
    if not text:
        return ""
    
    # Replace multiple spaces (including tabs and non-breaking spaces) with a single space
    text = re.sub(r'[ \t\u00A0\u2000-\u200B]+', ' ', text)

    
    # Normalize line breaks: replace 3 or more newlines with just 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Strip leading/trailing whitespace from each line and then from the whole string
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    return text.strip()



def clean_keywords(keywords: list[str]) -> list[str]:
    """Cleans a list of keywords by stripping spaces and removing duplicates."""
    if not keywords:
        return []
    cleaned = [k.strip() for k in keywords if k and k.strip()]
    return list(dict.fromkeys(cleaned)) # Maintain order while removing duplicates
