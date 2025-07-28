import requests
import os
import random
from app import db
from app.models import QuestionPaper, Question

def create_paper_service(title, content, user_id=None):
    """
    Generate 30 exam questions using OpenAI API, save paper and questions to DB.
    Returns serialized paper with questions.
    """
    grade_level = content.get('grade_level') if isinstance(content, dict) else None
    timeline = content.get('timeline') if isinstance(content, dict) else None
    requirements = content.get('requirements') if isinstance(content, dict) else content
    file_content = content.get('file_content') if isinstance(content, dict) else None
    image_content = None
    # If an image file is uploaded, extract text using OCR
    if isinstance(content, dict) and 'file_image' in content and content['file_image']:
        try:
            from PIL import Image
            import io
            import pytesseract
            image_bytes = content['file_image']
            image = Image.open(io.BytesIO(image_bytes))
            image_content = pytesseract.image_to_string(image)
        except Exception:
            image_content = None

    # Load API keys from env
    api_keys = os.environ.get('OPENAI_API_KEYS', '').split(',')
    api_keys = [k.strip() for k in api_keys if k.strip()]
    if not api_keys or not api_keys[0]:
        raise Exception("No OpenAI API keys found in environment variable OPENAI_API_KEYS.")
    api_key = random.choice(api_keys)
    if not api_key.startswith('sk-'):
        raise Exception("Invalid OpenAI API key format. Key must start with 'sk-'.")

    # If file is attached, extract topic(s) and special requests using AI
    extracted_topics = None
    extracted_special = None
    file_or_image_content = file_content or image_content
    if file_or_image_content:
        extract_prompt = (
            "You are an expert academic assistant. Given the following file content, extract the main topic or topics (as a comma-separated list) and any special requests or instructions for question generation (such as 'focus on applications', 'include diagrams', etc). "
            "If no special requests are found, return 'None'.\n"
            f"---\n{file_or_image_content}\n---\n"
            "Respond in JSON as: {\"topics\": [list of topics], \"special_requests\": [list of special requests or []]}"
        )
        extract_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an academic assistant."},
                    {"role": "user", "content": extract_prompt}
                ],
                "max_tokens": 400,
                "temperature": 0.0
            }
        )
        try:
            extract_data = extract_response.json()
            import json as _json
            ai_extract = extract_data['choices'][0]['message']['content']
            extract_json = _json.loads(ai_extract)
            extracted_topics = extract_json.get('topics')
            extracted_special = extract_json.get('special_requests')
        except Exception:
            extracted_topics = None
            extracted_special = None

    # Build the final topic and special request for question generation
    final_topics = ', '.join(extracted_topics) if extracted_topics else title
    final_special = ', '.join(extracted_special) if extracted_special else (requirements if requirements else '')

    # Build the main prompt for question generation
    prompt = (
        f"You are an advanced academic question generator. Research the topic(s): '{final_topics}'. "
        f"Special requests: {final_special}. "
        f"Generate a set of questions for the grade level: {grade_level or 'Unspecified'}. "
        f"The complexity, vocabulary, and depth should match this grade level. "
        f"Time allowed for the paper: {timeline or 'Unspecified'}. "
        + (f"\n\nThe following file or image content should be used as the main source material for generating questions. Use its facts, structure, and details wherever possible.\n---\n{file_or_image_content}\n---\n" if file_or_image_content else "")
        + "Use Bloom's taxonomy (remember, understand, apply, analyze, evaluate, create), real-world scenarios, and higher-order thinking. "
        "Include: "
        "10 Multiple Choice Questions (MCQ) with 4 plausible options (A-D), only one correct, and 3 strong distractors. Each MCQ should require analysis, synthesis, or evaluation, not just recall. Mark the correct answer. "
        "10 Very Short Answer Questions (1-2 sentences) that require precise, critical responses, not just definitions. "
        "10 Short Answer Questions (2-4 sentences) that require explanation, comparison, or application. "
        "7 Long Answer/Essay Questions (1+ paragraphs) that require argumentation, critical analysis, or creative synthesis. "
        "Format the output as sections: 'Multiple Choice', 'Very Short Answer', 'Short Answer', 'Long Answer'. "
        "For MCQ, use: 'Q: ...', then options A-D, then 'Answer: ...'. For others, use 'Q: ...'. "
        "Number all questions. Use real-world or novel scenarios where possible. "
        f"At the top of the paper, display: 'Time Allowed: {timeline or 'Unspecified'}'. "
    )

    import logging
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an academic assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.7
            }
        )
        if response.status_code != 200:
            logging.error(f"OpenAI API error: {response.status_code} {response.text}")
            raise Exception(f"OpenAI API error: {response.status_code} {response.text}")
        data = response.json()
        ai_content = data['choices'][0]['message']['content']

        # Advanced parsing: split by new sections and question types
        import re
        sections = re.split(r'(?i)^(Multiple Choice|Very Short Answer|Short Answer|Long Answer)\s*:?$', ai_content, flags=re.MULTILINE)
        questions = []
        section_map = {"Multiple Choice": [], "Very Short Answer": [], "Short Answer": [], "Long Answer": []}
        current_section = None
        for part in sections:
            part = part.strip()
            if part in section_map:
                current_section = part
            elif current_section:
                # Split questions by Q: marker
                qs = re.split(r'\n(?=Q: )', part)
                for q in qs:
                    q = q.strip()
                    if q:
                        section_map[current_section].append(q)
                        questions.append(q)

        # Fallback: if parsing fails, just split by Q: or newlines
        if not questions:
            questions = re.split(r'\nQ: ', ai_content)
            questions = [q if q.startswith('Q:') else 'Q: ' + q for q in questions if q.strip()]

        # Limit to 37 questions (10+10+10+7)
        questions = questions[:37]

        # Validate user_id
        if user_id is None:
            raise Exception('user_id is required and cannot be null.')
        # Create the QuestionPaper record
        paper = QuestionPaper(title=title, user_id=user_id)
        db.session.add(paper)
        db.session.commit()  # Commit to get paper.id

        # Create Question records linked to paper
        for question_text in questions:
            question = Question(text=question_text, question_paper_id=paper.id)
            db.session.add(question)

        db.session.commit()  # Save all questions

        # Prepare serialized return data
        return {
            "id": paper.id,
            "title": paper.title,
            "questions": [q.text for q in paper.questions],
            "grade_level": grade_level,
            "timeline": timeline
        }
    except Exception as e:
        fallback_questions = [
          f"Q: What is the main idea of {title}?",
            f"Q: Explain the significance of {requirements}.",
            "Q: List three key points discussed.",
            "Q: How does this topic relate to current events?",
            "Q: What are possible future developments?",
            # Add some MCQ examples
            f"Q: Which of the following best describes {title}?\nA) Option 1\nB) Option 2\nC) Option 3\nD) Option 4\nAnswer: A",
            f"Q: What is a real-world application of {title}?",
            f"Q: Write a very short answer about {title}."
        ]
        # Optionally, create a fallback paper and questions in DB or just return fallback data
        if user_id is None:
            raise Exception('user_id is required and cannot be null.')
        paper = QuestionPaper(title=title, user_id=user_id)
        db.session.add(paper)
        db.session.commit()
        for question_text in fallback_questions:
            question = Question(text=question_text, question_paper_id=paper.id)
            db.session.add(question)
        db.session.commit()
        return {
            "id": paper.id,
            "title": paper.title,
            "questions": [q.text for q in paper.questions],
            "grade_level": grade_level,
            "timeline": timeline,
            "error": str(e)
        }


