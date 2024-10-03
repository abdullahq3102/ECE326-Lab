from bottle import route, run, request, template, redirect

# In-memory storage for search history and word counts
history = {}

# Function to process the query and calculate word frequencies
def process_query(query):
    words = query.lower().split()
    word_count = {}
    
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1

        # Update history for the top 20 words
        history[word] = history.get(word, 0) + 1

    return word_count

# Home Page (Search Page)
@route('/')
def search():
    # Pass the top 20 words from the history to the template
    sorted_history = sorted(history.items(), key=lambda x: x[1], reverse=True)[:20]
    return template('templates/search.html', history=sorted_history)

# Result Page
@route('/results')
def results():
    query = request.query.keywords
    if not query:
        redirect('/')

    # Process the query and get the word count
    word_count = process_query(query)
    return template('templates/results.html', query=query, word_count=word_count)

# Run the server
run(host='localhost', port=8081, debug=True)
