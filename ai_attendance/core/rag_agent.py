# -*- coding: utf-8 -*-
import os
import re
import json
import math
import PyPDF2
import docx
import urllib.parse
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import List, Tuple

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

# -------------------------------------------------------------
# Configure Gemini AI
# -------------------------------------------------------------
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
if GEMINI_API_KEY:
    GEMINI_API_KEY = GEMINI_API_KEY.strip('\"\'')
if GEMINI_API_KEY and HAS_GENAI:
    genai.configure(api_key=GEMINI_API_KEY)


# -------------------------------------------------------------
# TEXT EXTRACTION HELPERS
# -------------------------------------------------------------

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
        text += extract_text_from_docx(file_path)
    elif ext in ['.txt', '.csv']:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text += f.read()
        except Exception:
            pass
    return text + "\n\n"


def extract_youtube_transcript(url):
    if not HAS_YT:
        return "YouTube Transcript extraction library not installed."

    def _fetch():
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
        return " ".join([t.text for t in transcript])

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch)
            return future.result(timeout=8)   # hard 8-second cap
    except FuturesTimeoutError:
        print(f"[YT] Transcript fetch timed out for {url}")
        return "YouTube transcript could not be fetched (timeout)."
    except Exception as e:
        print(f"Error fetching YT transcript for {url}: {e}")
        return f"Could not fetch transcript: {e}"


def extract_website_text(url):
    if not HAS_BS4:
        return "Website parsing library not installed."
    try:
        response = requests.get(url, timeout=6)   # reduced from 10 → 6s
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator=' ', strip=True)
        return text[:15000]   # cap at 15k chars to keep chunking fast
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


# -------------------------------------------------------------
# CHUNKING  (Overlapping Sliding-Window)
# -------------------------------------------------------------
CHUNK_SIZE = 400        # words per chunk  (was 500 – smaller = faster)
CHUNK_OVERLAP = 60     # overlapping words between consecutive chunks
MAX_CHUNKS_RETURNED = 5 # top-k chunks fed into the prompt (was 8)

# If the best TF-IDF cosine similarity is below this value the answer is
# very likely NOT in the selected notes -> trigger the fallback confirmation flow.
LOW_RELEVANCE_THRESHOLD = 0.08

# Session key that stores the question awaiting general-knowledge confirmation
PENDING_QUESTION_KEY = 'ai_pending_question'


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split *text* into overlapping word-level chunks so that each chunk
    fits comfortably inside a single embedding / ranking pass.
    """
    words = text.split()
    chunks = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start: start + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks


# -------------------------------------------------------------
# TF-IDF EMBEDDING / RETRIEVAL
# -------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, return word tokens."""
    return re.findall(r'\b[a-z]{2,}\b', text.lower())


def _tf(tokens: List[str]) -> dict:
    count = Counter(tokens)
    total = max(len(tokens), 1)
    return {t: c / total for t, c in count.items()}


def _idf(chunks_tokens: List[List[str]]) -> dict:
    """Inverse document frequency across all chunks."""
    N = len(chunks_tokens)
    df = defaultdict(int)
    for tokens in chunks_tokens:
        for t in set(tokens):
            df[t] += 1
    return {t: math.log((1 + N) / (1 + df[t])) + 1 for t in df}


def tfidf_retrieve(query: str, chunks: List[str], top_k: int = MAX_CHUNKS_RETURNED) -> Tuple[List[str], float]:
    """
    Rank *chunks* by cosine-similarity of their TF-IDF vectors against *query*.
    Returns (top_k_chunks: List[str], best_score: float).
    """
    if not chunks:
        return [], 0.0

    all_tokens = [_tokenize(c) for c in chunks]
    query_tokens = _tokenize(query)
    idf = _idf(all_tokens + [query_tokens])

    def tfidf_vector(tokens):
        tf = _tf(tokens)
        return {t: tf[t] * idf.get(t, 1.0) for t in tf}

    query_vec = tfidf_vector(query_tokens)
    if not query_vec:
        return chunks[:top_k], 0.0

    def cosine(vec):
        common = set(query_vec) & set(vec)
        if not common:
            return 0.0
        dot = sum(query_vec[t] * vec[t] for t in common)
        norm_q = math.sqrt(sum(v ** 2 for v in query_vec.values()))
        norm_c = math.sqrt(sum(v ** 2 for v in vec.values()))
        return dot / (norm_q * norm_c + 1e-9)

    scored = [(cosine(tfidf_vector(tokens)), chunk)
              for tokens, chunk in zip(all_tokens, chunks)]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score = scored[0][0] if scored else 0.0
    return [chunk for _, chunk in scored[:top_k]], best_score


# -------------------------------------------------------------
# CHAT HISTORY HELPERS
# -------------------------------------------------------------
CHAT_HISTORY_KEY = 'ai_chat_history_v2'
MAX_HISTORY_TURNS = 10   # keep last N full turns (user + assistant)


def get_chat_history(request) -> List[dict]:
    """Return chat history list from session."""
    return request.session.get(CHAT_HISTORY_KEY, [])


def save_chat_history(request, history: List[dict]):
    """Persist updated chat history to session (capped at MAX_HISTORY_TURNS)."""
    # Each turn = 2 messages (user + assistant) -> keep last MAX*2 messages
    trimmed = history[-(MAX_HISTORY_TURNS * 2):]
    request.session[CHAT_HISTORY_KEY] = trimmed
    request.session.modified = True


def clear_chat_history(request):
    """Wipe the chat history for this session."""
    request.session[CHAT_HISTORY_KEY] = []
    request.session.modified = True


def format_history_for_prompt(history: List[dict]) -> str:
    """Format history list as readable text for the prompt."""
    if not history:
        return "No previous conversation."
    lines = []
    for msg in history:
        role = "Student" if msg['role'] == 'user' else "AI Tutor"
        lines.append(f"{role}: {msg['text']}")
    return "\n".join(lines)


# -------------------------------------------------------------
# STRUCTURED RESPONSE PARSER
# -------------------------------------------------------------

def parse_structured_response(raw_text: str):
    """
    Gemini is asked to return a JSON block at the END of every answer:

        <<<JSON
        {"image_keywords": ["keyword1", "keyword2"]}
        JSON>>>

    This function splits that block from the human-readable answer text.
    Returns (answer_text: str, image_keywords: list).
    """
    marker_start = '<<<JSON'
    marker_end   = 'JSON>>>'
    image_keywords = []

    if marker_start in raw_text and marker_end in raw_text:
        try:
            pre, rest  = raw_text.split(marker_start, 1)
            json_block, _ = rest.split(marker_end, 1)
            parsed = json.loads(json_block.strip())
            if isinstance(parsed.get('image_keywords'), list):
                image_keywords = [str(k) for k in parsed['image_keywords'][:3]]
            answer_text = pre.strip()
        except Exception as e:
            print(f"[parse_structured_response] JSON parse error: {e}")
            answer_text = raw_text.strip()
    else:
        answer_text = raw_text.strip()

    return answer_text, image_keywords


# -------------------------------------------------------------
# CASUAL MESSAGE DETECTOR
# -------------------------------------------------------------

# Single-word or very short greetings / social phrases that are NOT
# topic questions and should never trigger the RAG confirmation flow.
_CASUAL_PATTERNS = {
    'hi', 'hii', 'hiii', 'hello', 'hey', 'helo', 'hlo',
    'bye', 'goodbye', 'good bye', 'good night', 'good morning',
    'good afternoon', 'good evening',
    'thanks', 'thank you', 'thankyou', 'thx', 'ty',
    'ok', 'okay', 'sure', 'alright', 'got it', 'noted',
    'yes', 'no', 'yep', 'nope', 'yeah', 'nah',
    'nice', 'cool', 'great', 'awesome', 'wow',
    'how are you', 'how r u', 'whats up', "what's up", 'sup',
    'who are you', 'what are you', 'are you a bot', 'are you ai',
}

def is_casual_message(text: str) -> bool:
    """
    Return True if *text* looks like a casual/greeting message that
    should get a direct conversational reply, NOT a RAG/topic search.

    Heuristics:
    - Normalised text matches a known casual phrase.
    - OR the message is very short (<= 3 words) AND contains no
      question-indicating words (what, how, why, explain, define, etc.).
    """
    normalised = text.lower().strip().rstrip('?!.')

    # Direct match against known casual phrases
    if normalised in _CASUAL_PATTERNS:
        return True

    # Repeated greeting chars: hiiii, heyyyy etc.
    if len(normalised) <= 6 and re.match(r'^h[aeiou]+$|^he+y+$', normalised):
        return True

    # Very short messages with no educational keywords
    words = normalised.split()
    if len(words) <= 2:
        educational_indicators = {
            'what', 'how', 'why', 'when', 'where', 'which', 'who',
            'explain', 'define', 'describe', 'difference', 'compare',
            'example', 'formula', 'concept', 'theory', 'topic',
        }
        if not any(w in educational_indicators for w in words):
            return True

    return False


# -------------------------------------------------------------
# MAIN API VIEW
# -------------------------------------------------------------

@csrf_exempt
@login_required
def ask_ai_api(request):
    """
    Endpoint for NotebookLM-style question asking with:
      * Overlapping text chunking
      * TF-IDF based top-k chunk retrieval
      * Persistent per-session chat history
      * Smart fallback: if notes don't contain the answer, asks the user
        whether to answer from general knowledge

    POST /core/student_materials/ask_ai/
    Body (JSON):
      {
        "question":              "...",
        "material_ids":          [1, 2],
        "student_note_ids":      [3],
        "clear_history":         false,   // optional — wipe chat history
        "use_general_knowledge": false    // optional — bypass notes & answer freely
      }

    When content is NOT found in notes the response includes:
      { "needs_confirmation": true, "answer": "<polite message asking user>", ... }

    Frontend should show a 'Yes, answer from general knowledge' button.
    On 'Yes', resend the SAME payload with "use_general_knowledge": true
    (question field can be omitted — the pending question is stored in session).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        question              = data.get('question', '').strip()
        material_ids          = data.get('material_ids', [])
        student_note_ids      = data.get('student_note_ids', [])
        should_clear          = data.get('clear_history', False)
        use_general_knowledge = data.get('use_general_knowledge', False)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    # -- Optionally clear history ------------------------------
    if should_clear:
        clear_chat_history(request)
        request.session.pop(PENDING_QUESTION_KEY, None)

    # -- If user approved general-knowledge fallback -----------
    # Retrieve the saved pending question from session if none supplied
    if use_general_knowledge and not question:
        question = request.session.get(PENDING_QUESTION_KEY, '')

    if not question or (not material_ids and not student_note_ids and not use_general_knowledge):
        return JsonResponse({'error': 'Question and at least one material/note are required.'}, status=400)

    if not HAS_GENAI:
        return JsonResponse(
            {'error': 'Google Generative AI library is not installed. Run: pip install google-generativeai'},
            status=501
        )

    if not GEMINI_API_KEY:
        return JsonResponse({'error': 'AI API key not configured on the server.'}, status=501)

    # -- Auth check ------------------------------------------
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Only students can use this feature.'}, status=403)

    student_name = request.user.get_full_name() or request.user.username
    chat_history = get_chat_history(request)
    history_text = format_history_for_prompt(chat_history)

    # ==========================================================
    # PATH 0 — Casual / greeting message (no RAG needed)
    # ==========================================================
    if is_casual_message(question) and not use_general_knowledge:
        casual_prompt = f"""You are a friendly AI tutor assistant called SUKU, helping a student named {student_name}.
The student sent a casual message. Reply in a warm, friendly, and concise way.
Do NOT mention documents, notes, or ask about topics.
Keep it short (1-3 sentences max).

=== CONVERSATION HISTORY ===
{history_text}

=== STUDENT MESSAGE ===
{question}

=== YOUR REPLY ==="""
        try:
            model    = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(casual_prompt)
            answer   = response.text

            chat_history.append({'role': 'user',      'text': question})
            chat_history.append({'role': 'assistant',  'text': answer})
            save_chat_history(request, chat_history)

            return JsonResponse({
                'answer': answer,
                'source': 'casual',
                'needs_confirmation': False,
                'history_turns': len(chat_history) // 2,
            })

        except Exception as e:
            print(f"Gemini API Error (casual): {e}")
            return JsonResponse({'error': f'Failed to generate response: {str(e)}'}, status=500)

    # ==========================================================
    # PATH A — General Knowledge Answer (user explicitly approved)
    # ==========================================================
    if use_general_knowledge:
        # Clear the stored pending question once we act on it
        request.session.pop(PENDING_QUESTION_KEY, None)

        gk_prompt = f"""You are an intelligent AI tutor for a student named {student_name}.

The student asked a question that was NOT found in their class notes. They have explicitly
asked you to answer from your general knowledge. Provide a clear, accurate, student-friendly
answer. Mention at the start that this answer comes from general knowledge, not their class notes.

AFTER your complete answer, append EXACTLY this block (no extra text outside it):
<<<JSON
{{"image_keywords": ["<keyword1>", "<keyword2>", "<keyword3>"]}}
JSON>>>
Replace the placeholders with 2-3 short visual image-search phrases relevant to the question.

=== CONVERSATION HISTORY ===
{history_text}

=== STUDENT QUESTION ===
{question}

=== AI TUTOR RESPONSE (from general knowledge) ==="""

        try:
            model    = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(gk_prompt)
            answer, image_keywords = parse_structured_response(response.text)

            chat_history.append({'role': 'user',      'text': question})
            chat_history.append({'role': 'assistant',  'text': answer})
            save_chat_history(request, chat_history)

            return JsonResponse({
                'answer': answer,
                'source': 'general_knowledge',
                'history_turns': len(chat_history) // 2,
                'image_keywords': image_keywords,
            })
        except Exception as e:
            print(f"Gemini API Error (GK): {e}")
            return JsonResponse({'error': f'Failed to generate response: {str(e)}'}, status=500)

    # ==========================================================
    # PATH B — Normal RAG flow
    # ==========================================================

    # -- Fetch materials / notes ------------------------------
    materials     = CourseMaterial.objects.filter(id__in=material_ids)
    student_notes = StudentNote.objects.filter(id__in=student_note_ids, student=student)

    if not materials.exists() and not student_notes.exists():
        return JsonResponse({'error': 'No valid materials found.'}, status=404)

    # -- Extract raw text -------------------------------------
    raw_text_parts = []

    for material in materials:
        if student.year and material.year and student.year.lower() != material.year.lower():
            continue
        if student.section and material.section and student.section.lower() != material.section.lower():
            continue
        part = get_text_from_material(material)
        if part.strip():
            raw_text_parts.append(part)

    for note in student_notes:
        part = get_text_from_student_note(note)
        if part.strip():
            raw_text_parts.append(part)

    if not raw_text_parts:
        return JsonResponse({'error': 'Could not extract text from the selected documents or links.'}, status=400)

    full_text = "\n\n".join(raw_text_parts)

    # -- CHUNKING ---------------------------------------------
    all_chunks = chunk_text(full_text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

    # -- TF-IDF RETRIEVAL -------------------------------------
    recent_turns   = chat_history[-4:]  # last 2 turns for query enrichment
    enriched_query = question
    if recent_turns:
        enriched_query = " ".join(m['text'] for m in recent_turns) + " " + question

    relevant_chunks, best_score = tfidf_retrieve(enriched_query, all_chunks, top_k=MAX_CHUNKS_RETURNED)
    retrieved_context = "\n\n---\n\n".join(relevant_chunks)

    # -- Detect low-relevance (content not in notes) -----------
    # Only trigger confirmation for real topic questions, not casual chat.
    content_not_in_notes = (best_score < LOW_RELEVANCE_THRESHOLD) and not is_casual_message(question)

    if content_not_in_notes:
        # Store question in session so user doesn't have to retype it
        request.session[PENDING_QUESTION_KEY] = question
        request.session.modified = True

        confirm_msg = (
            f"Hey {student_name}!  I looked through your selected notes and documents, "
            f"but I couldn't find information about **\"{question}\"** in them.\n\n"
            "Would you like me to answer this from my **general knowledge** instead? "
            "Just click **\"Yes, answer from general knowledge\"** below."
        )
        return JsonResponse({
            'answer': confirm_msg,
            'needs_confirmation': True,
            'source': 'notes',
            'chunks_used': 0,
            'total_chunks': len(all_chunks),
            'history_turns': len(chat_history) // 2,
        })

    # -- Build Prompt ------------------------------------------
    prompt = f"""You are an intelligent AI tutor for a student named {student_name}. Address them personally when appropriate.

Your task is to answer the student's question based ONLY on the provided context (retrieved excerpts from their class notes/assignments).

Rules:
- If the answer is NOT in the context, politely say the information is not in the selected notes.
- Cite the "Document Title" from the context whenever possible.
- Be concise, clear, and student-friendly.
- Maintain continuity with the conversation history below.
- AFTER your complete answer, append EXACTLY this block (no extra text outside it):
<<<JSON
{{"image_keywords": ["<keyword1>", "<keyword2>", "<keyword3>"]}}
JSON>>>
Replace the placeholders with 2-3 short visual image-search phrases most relevant to the student's question.

=== CONVERSATION HISTORY ===
{history_text}

=== RETRIEVED CONTEXT (most relevant excerpts) ===
{retrieved_context}

=== STUDENT QUESTION ===
{question}

=== AI TUTOR RESPONSE ==="""

    # -- Call Gemini -------------------------------------------
    try:
        model    = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        answer, image_keywords = parse_structured_response(response.text)

        # Append to chat history and persist
        chat_history.append({'role': 'user',      'text': question})
        chat_history.append({'role': 'assistant',  'text': answer})
        save_chat_history(request, chat_history)

        return JsonResponse({
            'answer': answer,
            'needs_confirmation': False,
            'source': 'notes',
            'chunks_used': len(relevant_chunks),
            'total_chunks': len(all_chunks),
            'history_turns': len(chat_history) // 2,
            'relevance_score': round(best_score, 4),
            'image_keywords': image_keywords,
        })

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return JsonResponse({'error': f'Failed to generate response: {str(e)}'}, status=500)


# -------------------------------------------------------------
# CLEAR HISTORY ENDPOINT
# -------------------------------------------------------------

@csrf_exempt
@login_required
def clear_ai_history_api(request):
    """
    POST /core/student_materials/clear_ai_history/
    Wipes the chat history for the current session.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    clear_chat_history(request)
    return JsonResponse({'status': 'ok', 'message': 'Chat history cleared.'})
