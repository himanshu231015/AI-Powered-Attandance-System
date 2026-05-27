import os
# Final server reload for correctly saved API key
import json
import PyPDF2
import docx
import urllib.parse
genai = None
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YT = True
except ImportError:
    HAS_YT = False

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import CourseMaterial, Student, StudentNote

# Configure Gemini AI using API Key from settings or environment
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
if GEMINI_API_KEY:
    GEMINI_API_KEY = GEMINI_API_KEY.strip('\"\'')
if GEMINI_API_KEY and HAS_GENAI:
    genai.configure(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    return text

def extract_text_from_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
    return text

def get_text_from_material(material):
    if not material.file:
        return ""
        
    file_path = material.file.path
    if not os.path.exists(file_path):
        return ""
        
    ext = os.path.splitext(file_path)[1].lower()
    text = f"--- Document Title: {material.title} ---\n"
    
    if ext == '.pdf':
        text += extract_text_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        # .doc might not work with python-docx, but we try
        text += extract_text_from_docx(file_path)
    elif ext in ['.txt', '.csv']:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text += f.read()
        except:
            pass
    return text + "\n\n"

def extract_youtube_transcript(url):
    if not HAS_YT:
        return "YouTube Transcript extraction library not installed."
    try:
        # Extract video ID
        parsed = urllib.parse.urlparse(url)
        video_id = ""
        if parsed.hostname == 'youtu.be':
            video_id = parsed.path[1:]
        elif parsed.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed.path == '/watch':
                video_id = urllib.parse.parse_qs(parsed.query).get('v', [None])[0]
        
        if not video_id:
            return "Could not parse YouTube Video ID."
            
        yt_api = YouTubeTranscriptApi()
        transcript = yt_api.fetch(video_id)
        text = " ".join([t.text for t in transcript])
        return text
    except Exception as e:
        print(f"Error fetching YT transcript for {url}: {e}")
        return f"Could not fetch transcript: {e}"

def extract_website_text(url):
    if not HAS_BS4:
        return "Website parsing library not installed."
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator=' ', strip=True)
        return text
    except Exception as e:
        print(f"Error fetching website {url}: {e}")
        return f"Could not fetch website content: {e}"

def get_text_from_student_note(note):
    text = f"--- Document Title: {note.title} ---\n"
    if note.note_type == 'youtube_link' and note.url:
        text += extract_youtube_transcript(note.url)
    elif note.note_type == 'web_link' and note.url:
        text += extract_website_text(note.url)
    elif note.note_type in ['pdf', 'doc'] and note.file:
        file_path = note.file.path
        if os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.pdf':
                text += extract_text_from_pdf(file_path)
            elif ext in ['.docx', '.doc']:
                text += extract_text_from_docx(file_path)
    return text + "\n\n"

@csrf_exempt
@login_required
def ask_ai_api(request):
    """
    Endpoint for NotebookLM-style question asking.
    Expects POST request with JSON payload: { "question": "...", "material_ids": [1, 2] }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        question = data.get('question')
        material_ids = data.get('material_ids', [])
        student_note_ids = data.get('student_note_ids', [])
    except Exception as e:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    if not question or (not material_ids and not student_note_ids):
        return JsonResponse({'error': 'Question and at least one material/note are required.'}, status=400)
        
    if not HAS_GENAI:
        return JsonResponse({'error': 'Google Generative AI library is not installed on the server. Please ask the administrator to run: pip install google-generativeai'}, status=501)
        
    if not GEMINI_API_KEY:
        return JsonResponse({'error': 'AI API key not configured on the server.'}, status=501)

    # Validate that student exists
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Only students can use this feature.'}, status=403)

    # Fetch materials and verify access
    materials = CourseMaterial.objects.filter(id__in=material_ids)
    student_notes = StudentNote.objects.filter(id__in=student_note_ids, student=student)
    
    if not materials.exists() and not student_notes.exists():
        return JsonResponse({'error': 'No valid materials found.'}, status=404)

    # Extract text from all selected materials
    context_text = ""
    for material in materials:
        # Simple access check based on year/section (can be expanded if needed)
        if student.year and material.year and student.year.lower() != material.year.lower():
            continue
        if student.section and material.section and student.section.lower() != material.section.lower():
            continue
            
        context_text += get_text_from_material(material)
        
    for note in student_notes:
        context_text += get_text_from_student_note(note)

    if not context_text.strip():
        return JsonResponse({'error': 'Could not extract text from the selected documents or links.'}, status=400)

    student_name = request.user.get_full_name() or request.user.username
    
    # Retrieve chat history from session
    chat_history = request.session.get('ai_chat_history', [])
    history_text = ""
    for msg in chat_history:
        if msg['role'] == 'user':
            history_text += f"Student: {msg['text']}\n"
        else:
            history_text += f"AI Tutor: {msg['text']}\n"

    # Prepare prompt for Gemini
    prompt = f"""
You are an intelligent AI tutor for a student named {student_name}. Address them personally when appropriate.
Your task is to answer the student's question based ONLY on the provided context materials (their class notes/assignments).

If the answer is not contained in the context, politely inform the student that the information is not available in the selected notes, but DO NOT try to answer from outside knowledge. Provide citations to the Document Title where possible.

--- PREVIOUS CHAT HISTORY ---
{history_text if history_text else "No previous history."}

--- CONTEXT (Student Notes) ---
{context_text[:150000]}  # Limit context to avoid hitting free-tier token limits (approx 35k tokens)

--- STUDENT QUESTION ---
{question}

--- AI TUTOR RESPONSE ---
"""

    try:
        # Use gemini-2.5-flash as it is fast, cheap, and has a large token context window
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        answer = response.text
        
        # Save to session history (keep last 10 messages)
        chat_history.append({'role': 'user', 'text': question})
        chat_history.append({'role': 'assistant', 'text': answer})
        request.session['ai_chat_history'] = chat_history[-10:]
        request.session.modified = True
        
        return JsonResponse({'answer': answer})
        
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return JsonResponse({'error': f'Failed to generate response: {str(e)}'}, status=500)
