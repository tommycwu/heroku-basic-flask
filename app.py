import os
import psycopg2

from flask import Flask, render_template

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(host='ec2-35-173-91-114.compute-1.amazonaws.com',
                            port='5432',
                            database='dc83nkrg1lpjr8',
                            user='trqegwenxqusrl',
                            password='b2387a4531c1f6f4620c531b87f25c3d535f1c4b9a9a9462f4f8c97ef5001543')
    return conn

@app.route("/")

def home():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT sandbox_name FROM sfdc_queue where table_id = 1')
    results = cur.fetchall()
    one = results[0]
    cur.close()
    conn.close()
    return render_template('home.html', size=one, animal='dog')


