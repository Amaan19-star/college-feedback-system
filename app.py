from flask import Flask, request, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from textblob import TextBlob
import sqlite3

app = Flask(__name__)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usn = request.form['usn']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('feedback.db')
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO students(usn,password) VALUES (?,?)",
            (usn, password)
        )

        conn.commit()
        conn.close()

    return render_template('register.html')
@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        usn = request.form['usn']
        password = request.form['password']

        conn = sqlite3.connect('feedback.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT password FROM students WHERE usn=?",
            (usn,)
        )

        data = cursor.fetchone()

        if data and check_password_hash(data[0], password):
            return redirect('/')

    return render_template('login.html')

def analyze_sentiment(feedback):
    polarity = TextBlob(feedback).sentiment.polarity

    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    return "Neutral"

@app.route('/admin', methods=['GET','POST'])
def admin():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin123":
            return redirect('/dashboard')

    return render_template('admin_login.html')
@app.route('/dashboard')
def dashboard():

    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM feedback"
    )

    feedbacks = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        feedbacks=feedbacks
    )
import matplotlib.pyplot as plt
from wordcloud import WordCloud
@app.route('/chart')
def chart():
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute("SELECT feedback FROM feedback")
    rows = cursor.fetchall()
    conn.close()

    sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for row in rows:
        sentiment = analyze_sentiment(row[0])
        sentiments[sentiment] += 1

    plt.figure()
    plt.bar(sentiments.keys(), sentiments.values(), color=['green', 'gray', 'red'])
    plt.title('Feedback Sentiment')
    plt.savefig('static/images/chart.png')
    plt.close()
    return redirect('/dashboard')

@app.route('/wordcloud')
def wordcloud():
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute("SELECT feedback FROM feedback")
    rows = cursor.fetchall()
    conn.close()

    text = " ".join(row[0] for row in rows if row[0])
    wc = WordCloud(width=800, height=400, background_color='white').generate(text)
    wc.to_file('static/images/wordcloud.png')
    return redirect('/dashboard')
import pandas as pd
from flask import send_file
@app.route('/csv')
def csv():

    conn = sqlite3.connect(
        'feedback.db'
    )

    df = pd.read_sql_query(
        "SELECT * FROM feedback",
        conn
    )

    df.to_csv(
        'reports/feedback.csv',
        index=False
    )

    return send_file(
        'reports/feedback.csv',
        as_attachment=True
    )
import importlib.util

reportlab_spec = importlib.util.find_spec("reportlab.pdfgen")
if reportlab_spec is not None:
    reportlab_pdfgen = importlib.import_module("reportlab.pdfgen")
    canvas = reportlab_pdfgen.canvas
else:
    canvas = None

@app.route('/pdf')
def pdf():
    if canvas is None:
        return "PDF generation library not available. Install reportlab to use this feature.", 503

    c = canvas.Canvas(
        'reports/report.pdf'
    )

    c.drawString(
        100, 800,
        "College Feedback Report"
    )

    c.save()

    return send_file(
        'reports/report.pdf',
        as_attachment=True
    )
from flask_mail import Mail, Message
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'app_password'
mail = Mail(app)

msg = Message(
    'New Feedback',
    recipients=['admin@gmail.com']
)

msg.body = "New feedback submitted."

try:
    mail.send(msg)
except Exception as e:
    print(f"Email sending failed: {e}")
from models.sentiment_model import predict # pyright: ignore[reportMissingImports]
result = predict(feedback) # pyright: ignore[reportUndefinedVariable]
sentiment = result[0]['label']