"""Cover letter rendering and AI generation."""
import json

from app.core.config import settings


TEMPLATE_VARIABLES = [
    "{{company_name}}",
    "{{vacancy_title}}",
    "{{skills}}",
    "{{salary}}",
    "{{hr_name}}",
]


def render_template(template_body: str, context: dict) -> str:
    """Replace template variables with context values."""
    result = template_body
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", str(value or ""))
    return result


async def generate_ai_cover_letter(
    vacancy: dict,
    resume_skills: str,
    tone: str = "formal",
    length: str = "short",
) -> str:
    """Generate AI cover letter using OpenAI."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    company = vacancy.get("employer", {}).get("name", "the company")
    title = vacancy.get("name", "the position")
    description = vacancy.get("description", "")[:2000]

    tone_instruction = "formal and professional" if tone == "formal" else "friendly and conversational"
    length_instruction = "2-3 short paragraphs" if length == "short" else "4-5 detailed paragraphs"

    prompt = f"""Write a cover letter in Russian for a job application.
Company: {company}
Position: {title}
Job description excerpt: {description}
Candidate skills: {resume_skills}
Tone: {tone_instruction}
Length: {length_instruction}

Write only the cover letter body, no greetings header."""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
