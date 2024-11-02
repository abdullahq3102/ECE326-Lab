from bottle import route, run, request, template, redirect, static_file
from oauth2client.client import flow_from_clientsecrets, OAuth2Credentials
from googleapiclient.discovery import build
from beaker.middleware import SessionMiddleware
import json
import httplib2
import bottle
# Load Google OAuth secrets
with open("oathSecrets.json") as f:
    secrets = json.load(f)
CLIENT_ID = secrets["web"]["client_id"]
CLIENT_SECRET = secrets["web"]["client_secret"]

# In-memory storage for anonymous search history and session management
history = {}
session_opts = {
    'session.type': 'memory',
    'session.cookie_expires': 300,
    'session.auto': True
}
app = SessionMiddleware(bottle.app(), session_opts)

# Function to process query
def process_query(query):
    words = query.lower().split()
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1
        history[word] = history.get(word, 0) + 1
    return word_count

# Serve static files (logo)
@route('/static/<filename>')
def serve_static(filename):
    return static_file(filename, root='./static')

# Home Page
@route('/')
def home():
    session = request.environ.get('beaker.session')
    user_email = session.get('user_email', None)

    if user_email:
        # Signed-in mode
        return template('templates/search.html', history=session.get('user_history', []), user_email=user_email)
    else:
        # Anonymous mode
        sorted_history = sorted(history.items(), key=lambda x: x[1], reverse=True)[:20]
        return template('templates/search.html', history=sorted_history, user_email=None)

# Google Login
@route('/login')
def login():
    flow = flow_from_clientsecrets(
        'oathSecrets.json',
        scope='https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
        redirect_uri='http://localhost:8081/redirect'
    )
    auth_uri = flow.step1_get_authorize_url()
    redirect(auth_uri)

# Google Redirect
@route('/redirect')
def redirect_page():
    session = request.environ.get('beaker.session')
    code = request.query.get('code')
    flow = flow_from_clientsecrets(
        'oathSecrets.json',
        scope='https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
        redirect_uri='http://localhost:8081/redirect'
    )
    credentials = flow.step2_exchange(code)
    http_auth = credentials.authorize(httplib2.Http())
    oauth_service = build('oauth2', 'v2', http=http_auth)
    user_info = oauth_service.userinfo().get().execute()

    session['user_email'] = user_info.get('email')
    session['user_history'] = []
    session.save()

    redirect('/')

# Search Results
@route('/results')
def results():
    session = request.environ.get('beaker.session')
    query = request.query.keywords
    if not query:
        redirect('/')

    word_count = process_query(query)

    # Store search history if logged in
    if session.get('user_email'):
        user_history = session.get('user_history', [])
        user_history.insert(0, query)  # Add latest search to history
        session['user_history'] = user_history[:10]  # Keep only the last 10 searches
        session.save()

    return template('templates/results.html', query=query, word_count=word_count, user_email=session.get('user_email'))

# Logout
@route('/logout')
def logout():
    session = request.environ.get('beaker.session')
    session.delete()  # Clear session data
    redirect('/')

# Run the server with session middleware
if __name__ == "__main__":
    run(app=app, host='localhost', port=8081, debug=True)
