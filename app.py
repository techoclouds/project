import os
import logging
from flask import Flask, request, redirect, jsonify
import random
import string
import psycopg2
import redis
import requests
import time
from bs4 import BeautifulSoup

# Configure Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Flask app
app = Flask(__name__)

# Environment Variables
DB_URL = os.getenv("DATABASE_URL", "postgresql://urlshortener:password@db:5432/urlshortener_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

# Connect to Redis
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def get_db_connection():
    logging.debug("Establishing a new PostgreSQL database connection")
    return psycopg2.connect(DB_URL)

def init_db():
    logging.debug("Initializing the database if not already initialized")
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS urls (
                                  id SERIAL PRIMARY KEY,
                                  short_code TEXT UNIQUE NOT NULL,
                                  long_url TEXT NOT NULL,
                                  title TEXT,
                                  description TEXT,
                                  word_count INTEGER,
                                  full_text TEXT
                              )''')
            conn.commit()
    logging.info("Database initialized")

def generate_short_code():
    logging.debug("Generating a unique short code")
    while True:
        short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        logging.debug(f"Generated short code candidate: {short_code}")
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM urls WHERE short_code = %s', (short_code,))
                if not cursor.fetchone():
                    logging.debug(f"Short code '{short_code}' is unique")
                    return short_code
                else:
                    logging.debug(f"Short code '{short_code}' already exists, regenerating...")

def fetch_metadata(url):
    try:
        logging.debug(f"Fetching metadata for URL: {url}")
        if not url.startswith("http"):
            url = "https://" + url
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.title.string.strip() if soup.title else 'No title'
        description_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        description = description_tag["content"].strip() if description_tag else "No description"

        full_text = ' '.join(soup.stripped_strings)
        word_count = len(full_text.split())

        logging.debug(f"Metadata fetched: title='{title}', description='{description}', word_count={word_count}")
        return title, description, word_count, full_text
    except Exception as e:
        logging.error(f"Error fetching metadata: {e}")
        return 'No title', 'No description', 0, ''

@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()
    long_url = data.get('long_url')
    if not long_url:
        logging.warning("Shortening request missing 'long_url'")
        return jsonify({'error': 'Missing long_url'}), 400

    short_code = generate_short_code()
    title, description, word_count, full_text = fetch_metadata(long_url)

    # Store in PostgreSQL
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO urls (short_code, long_url, title, description, word_count, full_text) VALUES (%s, %s, %s, %s, %s, %s)',
                (short_code, long_url, title, description, word_count, full_text)
            )
            conn.commit()
    logging.info(f"✅ Shortened URL stored: {short_code} -> {long_url}")

    short_url = f"{FRONTEND_URL}/go/{short_code}"
    return jsonify({'short_url': short_url, 'title': title, 'description': description, 'word_count': word_count, 'full_text': full_text})

@app.route('/go/<short_code>', methods=['GET'])
def redirect_url(short_code):
    logging.debug(f"Received request to redirect short_code: '{short_code}'")

    # Step 1: Check Redis cache first
    long_url = redis_client.get(short_code)
    if long_url:
        logging.info(f"🔵 Cache HIT: '{short_code}' -> '{long_url}'")
        return force_absolute_redirect(long_url)

    logging.warning(f"⚠️ Cache MISS for '{short_code}', querying PostgreSQL")

    # Step 2: Query PostgreSQL
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT long_url FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()

            if result and result[0]:
                long_url = result[0]
                redis_client.set(short_code, long_url, ex=3600)  # cache it
                logging.info(f"✅ PostgreSQL hit: '{short_code}' -> '{long_url}'")
                return force_absolute_redirect(long_url)

    logging.error(f"❌ Short URL '{short_code}' not found in PostgreSQL")
    return jsonify({'error': 'Short URL not found'}), 404



@app.route('/api/search', methods=['GET'])
def search_urls():
    """Search for URLs using pagination & count total results."""
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 50))
    offset = (page - 1) * size

    if not query:
        return jsonify({"total_results": 0, "data": []})

    logging.info(f"🔍 Searching for: {query} | Page: {page} | Size: {size}")

    search_start = time.time()
    total_results = 0

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # First, get the total count of matching results
            cursor.execute('''
                SELECT COUNT(*) FROM urls
                WHERE lower(short_code) LIKE %s OR lower(long_url) LIKE %s 
                      OR lower(title) LIKE %s OR lower(description) LIKE %s 
                      OR lower(full_text) LIKE %s
            ''', (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
            total_results = cursor.fetchone()[0]

            # Fetch paginated results
            cursor.execute('''
                SELECT short_code, long_url, title, description, word_count, full_text
                FROM urls
                WHERE lower(short_code) LIKE %s OR lower(long_url) LIKE %s 
                      OR lower(title) LIKE %s OR lower(description) LIKE %s 
                      OR lower(full_text) LIKE %s
                ORDER BY id DESC
                LIMIT %s OFFSET %s
            ''', (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", size, offset))
            
            results = cursor.fetchall()

    search_end = time.time()
    logging.info(f"✅ Query execution time: {search_end - search_start:.4f} sec")
    logging.info(f"🔢 Total results found: {total_results}")

    return jsonify({
        "total_results": total_results,
        "data": [
            {
                "short_code": r[0],
                "long_url": r[1],
                "title": r[2] or "No Title",
                "description": r[3] or "No Description",
                "word_count": r[4] or 0,
                "full_text": r[5] or "No text available"
            }
            for r in results
        ]
    })


def force_absolute_redirect(url):
    logging.debug(f"Ensuring absolute URL redirect for: '{url}'")
    if not url.startswith("http"):
        url = "https://" + url
        logging.debug(f"Modified URL to absolute: '{url}'")
    logging.info(f"🔀 Redirecting user to: '{url}'")
    return redirect(url, code=302)

if __name__ == '__main__':
    logging.info("🚀 Starting Flask application")
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
