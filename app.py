import os
import logging
from flask import Flask, request, redirect, jsonify
import random
import string
import psycopg2
import redis

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
                                  long_url TEXT NOT NULL
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

@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()
    long_url = data.get('long_url')
    if not long_url:
        logging.warning("Shortening request missing 'long_url'")
        return jsonify({'error': 'Missing long_url'}), 400

    short_code = generate_short_code()

    # Store in PostgreSQL
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO urls (short_code, long_url) VALUES (%s, %s)',
                (short_code, long_url)
            )
            conn.commit()
    logging.info(f"✅ Shortened URL stored: {short_code} -> {long_url}")

    short_url = f"{FRONTEND_URL}/go/{short_code}"
    return jsonify({'short_url': short_url})

@app.route('/go/<short_code>', methods=['GET'])
def redirect_url(short_code):
    logging.debug(f"Received request to redirect short_code: '{short_code}'")

    # Step 1: Check Redis cache first
    long_url = redis_client.get(short_code)
    if long_url:
        logging.info(f"🔵 Cache HIT: '{short_code}' -> '{long_url}'")
        return force_absolute_redirect(long_url)

    logging.debug(f"⚠️ Cache miss for '{short_code}', querying PostgreSQL with 2-sec delay")

    # Step 2: Query PostgreSQL with artificial delay (simulate DB latency)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT pg_sleep(2), long_url FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()

            if result and result[1]:
                long_url = result[1]
                logging.debug(f"Short code '{short_code}' found in PostgreSQL, caching in Redis")
                redis_client.set(short_code, long_url, ex=3600)  # cache it

                logging.info(f"✅ PostgreSQL hit after delay: '{short_code}' -> '{long_url}'")
                return force_absolute_redirect(long_url)

    logging.error(f"❌ Short URL '{short_code}' not found in PostgreSQL")
    return jsonify({'error': 'Short URL not found'}), 404

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
