import streamlit as st
import google.generativeai as genai
import PyPDF2
import json
import io
import datetime
from dotenv import load_dotenv
import os

# ==============================
# 🔧 CONFIGURATION
# ==============================
load_dotenv()

# Get API key from environment
api_key = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=api_key)

# Load model
model = genai.GenerativeModel("gemini-2.5-pro")


# ==============================
# 📘 PDF TEXT EXTRACTION
# ==============================

def extract_text_from_pdfs(uploaded_files):
    text = ""
    for uploaded_file in uploaded_files:
        reader = PyPDF2.PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text.strip()

# ==============================
# 🧠 GEMINI MCQ GENERATION
# ==============================

def generate_mcqs(text, num_questions=20):
    prompt = f"""
    Generate {num_questions} multiple choice questions from the text below.
    Each question should have 4 options (A–D) and one correct answer.
    Format strictly as:
    Q1. <question>
    A) <option>
    B) <option>
    C) <option>
    D) <option>
    Answer: <letter>

    Text:
    {text}
    """
    response = model.generate_content(prompt)
    return response.text

# ==============================
# 📑 PARSE MCQs
# ==============================

def parse_mcqs(text):
    mcqs = []
    current_q = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Q") and "." in line:
            if current_q:
                mcqs.append(current_q)
            current_q = {"question": line, "options": [], "answer": None}
        elif line.startswith(("A)", "B)", "C)", "D)")):
            if current_q:
                current_q["options"].append(line)
        elif line.startswith("Answer:"):
            if current_q:
                current_q["answer"] = line.split(":")[-1].strip()
    if current_q:
        mcqs.append(current_q)
    return mcqs

# ==============================
# 🧾 SAVE LATEST QUIZ RESULT LOCALLY
# ==============================

def save_latest_result(mcqs, user_answers, score):
    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "score": score,
        "mcqs": mcqs,
        "user_answers": user_answers
    }
    with open("quiz_results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ==============================
# 🎨 STREAMLIT UI
# ==============================

st.set_page_config(page_title="Gemini 2.5 MCQ Quiz", page_icon="🧠", layout="centered")
st.title("🧠 NPTEL- Lecture-based MCQ Quiz")

uploaded_files = st.file_uploader("Upload your lecture PDFs (multiple allowed)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    with st.spinner("Extracting text from PDFs..."):
        text_data = extract_text_from_pdfs(uploaded_files)

    if st.button("Generate MCQs"):
        with st.spinner("Generating MCQs with Gemini 2.5..."):
            mcq_text = generate_mcqs(text_data)
            mcqs = parse_mcqs(mcq_text)
            st.session_state["mcqs"] = mcqs
            st.success(f"Generated {len(mcqs)} MCQs!")

# ==============================
# 🧩 QUIZ SECTION
# ==============================

if "mcqs" in st.session_state:
    st.header("📝 Take the Test")
    user_answers = {}

    for i, q in enumerate(st.session_state["mcqs"]):
        st.subheader(q["question"])
        selected = st.radio("Select your answer:", q["options"], key=f"q_{i}")
        user_answers[q["question"]] = selected

    if st.button("Submit Quiz"):
        correct = 0
        for q in st.session_state["mcqs"]:
            correct_option = q["answer"]
            user_selected = user_answers[q["question"]]
            if user_selected.startswith(correct_option):
                correct += 1

        total = len(st.session_state["mcqs"])
        score = round((correct / total) * 100, 2)

        st.success(f"✅ You scored {score}% ({correct}/{total} correct)")

        save_latest_result(st.session_state["mcqs"], user_answers, score)
        st.info("Your latest quiz results have been saved locally as 'quiz_results.json'.")