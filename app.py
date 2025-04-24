from flask import Flask, request, redirect, jsonify
import random
import string
import psycopg2
import os
import redis

app = Flask(__name__)
DB_URL = os.getenv("DATABASE_URL", "postgresql://urlshortener:password@db:5432/urlshortener_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS urls (
                                id SERIAL PRIMARY KEY,
                                short_code TEXT UNIQUE NOT NULL,
                                long_url TEXT NOT NULL
                              )''')
            conn.commit()

def generate_short_code():
    while True:
        short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM urls WHERE short_code = %s', (short_code,))
                if not cursor.fetchone():
                    return short_code

@app.route('/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()
    long_url = data.get('long_url')
    if not long_url:
        return jsonify({'error': 'Missing long_url'}), 400

    short_code = generate_short_code()
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('INSERT INTO urls (short_code, long_url) VALUES (%s, %s)', (short_code, long_url))
            conn.commit()

    redis_client.set(short_code, long_url, ex=3600)  # Cache for 1 hour

    return jsonify({'short_url': request.host_url + short_code})

@app.route('/<short_code>', methods=['GET'])
def redirect_url(short_code):
    long_url = redis_client.get(short_code)
    if long_url:
        return redirect(long_url)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT pg_sleep(2)")  # Simulate slow DB query **ONLY when fetching the URL**
            cursor.execute("SELECT long_url FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()

    if result:
        redis_client.set(short_code, result[0], ex=3600)  # Store in cache
        return redirect(result[0])
    else:
        return jsonify({'error': 'Short URL not found'}), 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

