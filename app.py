from bottle import route, run, request, template, redirect, static_file, error
from oauth2client.client import flow_from_clientsecrets, OAuth2Credentials
from googleapiclient.discovery import build
from beaker.middleware import SessionMiddleware
import json
import httplib2
import os
import bottle
import sqlite3
import time 
from spellchecker import SpellChecker
import re
spell = SpellChecker()

db_conn = sqlite3.connect("crawler_data.db")
db_conn.row_factory = sqlite3.Row


with open("oauthSecrets.json") as f:
    secrets = json.load(f)
CLIENT_ID = secrets["web"]["client_id"]
CLIENT_SECRET = secrets["web"]["client_secret"]

HISTORY_FILE = "user_search_history.json"

history = {}
session_opts = {
    'session.type': 'memory',
    'session.cookie_expires': 300,
    'session.auto': True
}
app = SessionMiddleware(bottle.app(), session_opts)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(user_email, search_history):
    all_history = load_history()
    all_history[user_email] = search_history
    with open(HISTORY_FILE, 'w') as f:
        json.dump(all_history, f)

def process_query(query):
    words = query.lower().split()
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1
        history[word] = history.get(word, 0) + 1
    return word_count

@route('/static/<filename>')
def serve_static(filename):
    return static_file(filename, root='./static')

@route('/')
def home():
    session = request.environ.get('beaker.session')
    user_email = session.get('user_email', None)

    if user_email:
    
        return template('templates/search.html', history=session.get('user_history', []), user_email=user_email)
    else:
    
        return template('templates/search.html', history=None, user_email=None)

@route('/login')
def login():
    flow = flow_from_clientsecrets(
        'oauthSecrets.json',
        scope='https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
        redirect_uri='http://localhost:8082/redirect'
    )
    auth_uri = flow.step1_get_authorize_url()
    redirect(auth_uri)

@route('/redirect')
def redirect_page():
    session = request.environ.get('beaker.session')
    code = request.query.get('code')
    flow = flow_from_clientsecrets(
        'oauthSecrets.json',
        scope='https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
        redirect_uri='http://localhost:8082/redirect'
    )
    credentials = flow.step2_exchange(code)
    http_auth = credentials.authorize(httplib2.Http())
    oauth_service = build('oauth2', 'v2', http=http_auth)
    user_info = oauth_service.userinfo().get().execute()


    user_email = user_info.get('email')
    session['user_email'] = user_email
    all_history = load_history()
    session['user_history'] = all_history.get(user_email, [])
    session.save()

    redirect('/')

# @route('/results')
# def results():
#     session = request.environ.get('beaker.session')
#     query = request.query.keywords
#     if not query:
#         redirect('/')

#     word_count = process_query(query)

#     if session.get('user_email'):
#         user_history = session.get('user_history', [])
#         user_history.insert(0, query) 
#         session['user_history'] = user_history[:10] 
#         save_history(session['user_email'], session['user_history']) 
#         session.save()

#     return template('templates/results.html', query=query, word_count=word_count, user_email=session.get('user_email'))

@route('/logout')
def logout():
    session = request.environ.get('beaker.session')
    session.delete() 
    redirect('/')
    
@route('/results')
def results():
    session = request.environ.get('beaker.session')
    query = request.query.keywords
    page = int(request.query.page or 1)  # Default to page 1 if no page parameter

    if not query:
        redirect('/')

    # Initialize math_result as None
    math_result = None

    # Check if the query is a mathematical expression
    math_pattern = r'^[\d\s\+\-\*/\(\)\.]+$'  # Regex to allow valid math expressions
    if re.match(math_pattern, query):
        try:
            math_result = eval(query)  # Compute the math result
        except Exception as e:
            math_result = None  # If eval fails, ignore it

    # If it's a math expression, show the result without querying the database
    if math_result is not None:
        processing_time = 0.0  # No need for heavy processing
        return template(
            'templates/results',
            query=query,
            math_result=math_result,
            results=[],
            total_results=0,
            current_page=1,
            total_pages=1,
            processing_time=processing_time,
            user_email=session.get('user_email'),
            corrections_made=False,
            corrected_query=None,
        )

    # Spell correction
    corrected_query = ' '.join(spell.correction(word) for word in query.split())
    corrections_made = corrected_query != query

    # Check if cached results exist for the same query
    if session.get('last_query') == query:
        start_time = time.time()
        print("Using cached results")
        all_results = session.get('cached_results', [])
        processing_time = time.time() - start_time  # Stop timing
    else:
        print("Fetching new results")
        start_time = time.time()  # Start timing
        keywords = [word.lower() for word in query.split()]
        cur = db_conn.cursor()

        # Get all document IDs for the given keywords
        doc_scores = {}
        for word in keywords:
            cur.execute("SELECT id FROM Lexicon WHERE word = ?", (word,))
            word_id_row = cur.fetchone()
            if not word_id_row:
                continue  # Skip this word if it doesn't exist in the lexicon

            word_id = word_id_row['id']
            cur.execute("SELECT doc_id FROM InvertedIndex WHERE word_id = ?", (word_id,))
            doc_ids = [row['doc_id'] for row in cur.fetchall()]

            for doc_id in doc_ids:
                cur.execute("SELECT score FROM PageRank WHERE doc_id = ?", (doc_id,))
                score_row = cur.fetchone()
                score = float(score_row['score']) if score_row else 0

                if doc_id in doc_scores:
                    doc_scores[doc_id] += score
                else:
                    doc_scores[doc_id] = score

        # Sort documents by their aggregated scores (descending)
        sorted_doc_scores = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

        # Fetch document details for the sorted document IDs
        all_results = []
        for doc_id, score in sorted_doc_scores:
            cur.execute("SELECT url, title FROM DocumentIndex WHERE id = ?", (doc_id,))
            doc_row = cur.fetchone()
            if doc_row:
                all_results.append({
                    'url': doc_row['url'],
                    'title': doc_row['title'],
                    'score': score
                })

        processing_time = time.time() - start_time  # Stop timing

        # Cache results in the session
        session['last_query'] = query
        session['cached_results'] = all_results
        session['processing_time'] = processing_time
        session.save()

    # Pagination logic
    results_per_page = 10
    total_results = len(all_results)
    total_pages = (total_results + results_per_page - 1) // results_per_page
    start_index = (page - 1) * results_per_page
    end_index = start_index + results_per_page
    results = [
        (result['url'], result['title'], result['score'])
        for result in all_results[start_index:end_index]
    ]

    return template(
        'templates/results',
        query=query,
        corrected_query=corrected_query,
        corrections_made=corrections_made,
        math_result=math_result,  # Ensure math_result is always passed
        results=results,
        total_results=total_results,
        current_page=page,
        total_pages=total_pages,
        processing_time=processing_time,
        user_email=session.get('user_email'),
    )


@error(404)
def error404(error):
    return template(
        'templates/error.html',
        message="The page you are looking for does not exist.",
        home_url="/"
    )

@error(500)
def error404(error):
    return template(
        'templates/error.html',
        message="The page you are looking for does not exist.",
        home_url="/"
    )


if __name__ == "__main__":
    # run(app=app, host='0.0.0.0', port=8082, debug=True)0
    run(app=app, host='localhost', port=8082, debug=True)
