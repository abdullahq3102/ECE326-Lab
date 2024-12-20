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
    
def is_math_expression(query):
    """Check if the query is a valid math expression, excluding single numbers."""
    try:
        result = eval(query)
        if isinstance(result, (int, float)) and query.isdigit():
            return False
        return True
    except (SyntaxError, NameError, ZeroDivisionError):
        return False
    
@route('/results')
def results():
    session = request.environ.get('beaker.session')
    query = request.query.keywords
    page = int(request.query.page or 1) 

    if not query:
        redirect('/')


    math_result = None

    if is_math_expression(query):
        try:
            math_result = eval(query)
            return template(
                'templates/results',
                query=query,
                math_result=math_result,
                results=[],
                total_results=0,
                current_page=page,
                total_pages=0,
                user_email=session.get('user_email'),
                processing_time=0,
                corrections_made=False,
                corrected_query=None
            )
        except Exception as e:
            math_result = None


    corrected_query = ' '.join(spell.correction(word) for word in query.split())
    corrections_made = corrected_query != query


    if session.get('last_query') == query:
        start_time = time.time()
        print("Using cached results")
        all_results = session.get('cached_results', [])
        processing_time = time.time() - start_time 
    else:
        print("Fetching new results")
        start_time = time.time() 
        keywords = [word.lower() for word in query.split()]
        cur = db_conn.cursor()

    
        doc_scores = {}
        for word in keywords:
            cur.execute("SELECT id FROM Lexicon WHERE word = ?", (word,))
            word_id_row = cur.fetchone()
            if not word_id_row:
                continue 

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

    
        sorted_doc_scores = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

    
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

        processing_time = time.time() - start_time 

    
        session['last_query'] = query
        session['cached_results'] = all_results
        session['processing_time'] = processing_time
        session.save()


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
        math_result=math_result, 
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
    run(app=app, host='0.0.0.0', port=8082, debug=True)
    # run(app=app, host='localhost', port=8082, debug=True)
