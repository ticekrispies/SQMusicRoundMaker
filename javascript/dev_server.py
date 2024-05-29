import json
import os

from flask import Flask, render_template
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)


@app.route("/")
def main_page():
    return render_template("sq-music.html")
