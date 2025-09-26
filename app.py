from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import spacy
import numpy as np
import os
from collections import defaultdict
#this is comment 2
app = Flask(__name__)

# Configure static file serving
app.static_folder = 'static'
app.static_url_path = '/static'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Synonym dictionary for rule-based keyword matching
SYNONYM_DICT = {
    # --- General Information ---
    "vision": ["goal", "aim", "objective", "aspiration", "outlook"],
    "mission": ["purpose", "mandate", "commitment", "direction"],
    "values": ["principles", "ethics", "beliefs", "standards", "virtues"],
    "history": ["background", "origin", "foundation", "establishment"],
    "institution": ["university", "school", "campus", "college"],

    # --- Admission & Enrollment ---
    "admission": ["entry", "acceptance", "application", "entrance"],
    "enrollment": ["registration", "sign-up", "matriculation", "joining"],
    "requirements": ["documents", "papers", "credentials", "needs", "prerequisites"],
    "transferee": ["transfer student", "shifter", "cross-registrant"],
    "exam": ["test", "assessment", "evaluation", "entrance exam"],
    "foreign": ["international", "non-local", "overseas"],

    # --- Academic Policies ---
    "grades": ["marks", "scores", "results", "ratings"],
    "grading": ["evaluation", "assessment", "marking system"],
    "subjects": ["courses", "classes", "units", "lectures"],
    "load": ["units", "course load", "subjects"],
    "probation": ["warning", "deficiency", "academic standing"],
    "disqualification": ["dismissal", "expulsion", "termination"],
    "records": ["transcript", "TOR", "academic file"],
    "attendance": ["presence", "absences", "participation"],
    "dishonesty": ["cheating", "plagiarism", "copying", "fraud"],

    # --- Fees & Scholarships ---
    "tuition": ["fees", "payment", "charges", "costs", "expenses", "schooling cost"],
    "refund": ["reimbursement", "repayment", "return"],
    "scholarship": ["grant", "financial aid", "assistance", "support", "sponsorship"],
    "discount": ["deduction", "reduction", "fee cut"],
    "installment": ["partial payment", "staggered payment", "deferred payment"],

    # --- Student Conduct & Discipline ---
    "rules": ["regulations", "policies", "guidelines", "protocols", "standards"],
    "discipline": ["sanctions", "punishment", "penalty", "conduct"],
    "offenses": ["violations", "infractions", "misconduct", "wrongdoing"],
    "dress code": ["uniform", "attire", "clothing policy", "appearance"],
    "harassment": ["bullying", "abuse", "discrimination", "violence"],

    # --- Student Services & Facilities ---
    "student": ["learner", "undergraduate", "enrollee", "pupil"],
    "teacher": ["professor", "instructor", "faculty", "educator"],
    "library": ["learning resource", "study area", "reading room", "resources"],
    "counseling": ["guidance", "advice", "support services"],
    "health": ["medical", "clinic", "infirmary", "wellness"],
    "organization": ["club", "association", "student group", "society"],
    "osa": ["office of student affairs", "student office", "welfare office"],

    # --- Co-Curricular & Extra-Curricular ---
    "activities": ["events", "programs", "seminars", "trainings", "competitions"],
    "sports": ["athletics", "games", "tournaments", "intramurals"],
    "volunteer": ["outreach", "service", "community work"],
    "leadership": ["student council", "officer", "representative"],

    # --- Graduation & Completion ---
    "graduation": ["commencement", "completion", "finishing school", "conferment"],
    "honors": ["awards", "recognition", "distinction", "achievements"],
    "diploma": ["certificate", "degree paper"],
    "clearance": ["sign-off", "exit form", "obligation check"],

    # --- Miscellaneous / Special Policies ---
    "leave": ["absence", "break", "time-off", "loa"],
    "withdrawal": ["dropping", "cancellation", "exit"],
    "shifting": ["change course", "transfer program", "move major"],
    "returnee": ["come back", "re-enroll", "continuing student"],
    "suspension": ["class stoppage", "cancellation", "holiday"],
    "emergency": ["crisis", "incident", "disaster", "urgent situation"]
}

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_md')
except OSError:
    print("Downloading spaCy model...")
    os.system('python -m spacy download en_core_web_md')
    nlp = spacy.load('en_core_web_md')

# Load FAQ dataset and prepare keyword index
try:
    with open(os.path.join(app.static_folder, 'faqs.json'), 'r') as f:
        faq_data = json.load(f)
        faqs = faq_data['faqs']
        
        # Create keyword index
        keyword_index = defaultdict(list)
        for i, faq in enumerate(faqs):
            # Process question text
            doc = nlp(faq['question'].lower())
            
            # Extract keywords and their lemmas
            keywords = set()
            for token in doc:
                if not token.is_stop and not token.is_punct:
                    keywords.add(token.text)
                    keywords.add(token.lemma_)
                    
                    # Add synonyms
                    for key, synonyms in SYNONYM_DICT.items():
                        if token.text in synonyms or token.lemma_ in synonyms:
                            keywords.update(synonyms)
                            keywords.add(key)
            
            # Index FAQ by keywords
            for keyword in keywords:
                keyword_index[keyword].append(i)
except FileNotFoundError:
    print("Error: faqs.json not found in static folder")
    faqs = []
    keyword_index = defaultdict(list)

def rule_based_search(query):
    """Enhanced keyword-based search with synonyms"""
    query = query.lower()
    matches = defaultdict(float)
    
    # Process query
    query_doc = nlp(query)
    query_keywords = set()
    
    # Extract keywords and synonyms from query
    for token in query_doc:
        if not token.is_stop and not token.is_punct:
            query_keywords.add(token.text)
            query_keywords.add(token.lemma_)
            
            # Add synonyms
            for key, synonyms in SYNONYM_DICT.items():
                if token.text in synonyms or token.lemma_ in synonyms:
                    query_keywords.update(synonyms)
                    query_keywords.add(key)
    
    # Find matches using keyword index
    for keyword in query_keywords:
        for faq_index in keyword_index[keyword]:
            matches[faq_index] += 1
    
    if matches:
        # Find best match
        best_match_index = max(matches.items(), key=lambda x: x[1])[0]
        score = matches[best_match_index] / len(query_keywords)
        
        if score > 0.3:  # Threshold for keyword match
            return faqs[best_match_index]
    
    return None

def nlp_search(query):
    """Enhanced semantic similarity search using spaCy"""
    query_doc = nlp(query)
    
    matches = []
    
    # Consider both question and answer content for matching
    for faq in faqs:
        # Calculate similarity with question
        question_doc = nlp(faq['question'])
        question_similarity = query_doc.similarity(question_doc)
        
        # Calculate similarity with answer (giving it less weight)
        answer_doc = nlp(faq['answer'])
        answer_similarity = query_doc.similarity(answer_doc) * 0.5
        
        # Combined similarity score
        total_similarity = max(question_similarity, answer_similarity)
        
        matches.append({
            'faq': faq,
            'score': total_similarity
        })
    
    if matches:
        matches.sort(key=lambda x: x['score'], reverse=True)
        best_match = matches[0]
        
        if best_match['score'] > 0.6:  # Adjusted threshold
            return best_match['faq']
    
    return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    user_question = request.json.get('question', '')
    
    if not user_question:
        return jsonify({
            'answer': 'Please ask a question.',
            'confidence': 0
        })

    # Try keyword-based search first
    result = rule_based_search(user_question)
    confidence = 0.9 if result else 0
    
    # If no good keyword match, try semantic search
    if not result:
        result = nlp_search(user_question)
        confidence = 0.7 if result else 0
    
    if result:
        # Process the answer for better readability
        answer = result['answer']
        
        return jsonify({
            'answer': answer,
            'confidence': confidence,
            'source': result['question']  # Include original question for context
        })
    
    # Suggest related topics if no exact match found
    query_doc = nlp(user_question)
    suggestions = []
    
    for faq in faqs:
        similarity = query_doc.similarity(nlp(faq['question']))
        if similarity > 0.4:  # Lower threshold for suggestions
            suggestions.append(faq['question'])
    
    if suggestions:
        response = "I couldn't find an exact match, but you might be interested in these topics:\n\n"
        response += "\n".join([f"• {q}" for q in suggestions[:3]])
        return jsonify({
            'answer': response,
            'confidence': 0.3,
            'suggestions': suggestions[:3]
        })
    
    return jsonify({
        'answer': "I couldn't find that specific information in the handbook. Please try rephrasing your question or contact the Registrar's Office for more detailed information.",
        'confidence': 0
    })

if __name__ == '__main__':
    app.run(debug=True)