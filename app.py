from flask import Flask, request, redirect, jsonify
import random
import string
import psycopg2
import os

app = Flask(__name__)
DB_URL = os.getenv("DATABASE_URL", "postgresql://urlshortener:password@db:5432/urlshortener_db")

# Create database connection
def get_db_connection():
    return psycopg2.connect(DB_URL)

# Create database and table if not exists
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS urls (
                                id SERIAL PRIMARY KEY,
                                short_code TEXT UNIQUE NOT NULL,
                                long_url TEXT NOT NULL
                              )''')
            conn.commit()

# Generate a unique short code
def generate_short_code():
    while True:
        short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM urls WHERE short_code = %s", (short_code,))
                if not cursor.fetchone():
                    return short_code

# Shorten URL API
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
    
    return jsonify({'short_url': request.host_url + short_code})

# Redirect to long URL
@app.route('/<short_code>', methods=['GET'])
def redirect_url(short_code):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT pg_sleep(2)")
            cursor.execute('SELECT long_url FROM urls WHERE short_code = %s', (short_code,))
            result = cursor.fetchone()
    
    if result:
        return redirect(result[0])
    else:
        return jsonify({'error': 'Short URL not found'}), 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

