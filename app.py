import os
import psycopg2

from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html", size=os.environ['DB_USERNAME'], animal=os.environ['DB_PASSWORD'])


