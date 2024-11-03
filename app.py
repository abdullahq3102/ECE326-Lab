from bottle import route, run, request, template, redirect, static_file
from oauth2client.client import flow_from_clientsecrets, OAuth2Credentials
from googleapiclient.discovery import build
from beaker.middleware import SessionMiddleware
import json
import httplib2
import os
import bottle

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

@route('/results')
def results():
    session = request.environ.get('beaker.session')
    query = request.query.keywords
    if not query:
        redirect('/')

    word_count = process_query(query)

    if session.get('user_email'):
        user_history = session.get('user_history', [])
        user_history.insert(0, query) 
        session['user_history'] = user_history[:10] 
        save_history(session['user_email'], session['user_history']) 
        session.save()

    return template('templates/results.html', query=query, word_count=word_count, user_email=session.get('user_email'))

@route('/logout')
def logout():
    session = request.environ.get('beaker.session')
    session.delete() 
    redirect('/')

if __name__ == "__main__":
    run(app=app, host='0.0.0.0', port=8082, debug=True)
