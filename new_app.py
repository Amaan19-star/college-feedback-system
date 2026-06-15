# ── Imports ──────────────────────────────────────────────────────────────────
from flask import Flask, request, render_template, redirect, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from textblob import TextBlob
from flask_mail import Mail, Message
from wordcloud import WordCloud
import sqlite3
import importlib.util
import matplotlib.pyplot as plt
import pandas as pd

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Mail config ───────────────────────────────────────────────────────────────
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'   # replace
app.config['MAIL_PASSWORD'] = 'app_password'           # replace
mail = Mail(app)

# ── Optional: reportlab (PDF) ─────────────────────────────────────────────────
_reportlab_spec = importlib.util.find_spec("reportlab.pdfgen")
if _reportlab_spec is not None:
    from reportlab.pdfgen import canvas as _canvas
else:
    _canvas = None

# ── Optional: custom sentiment model ─────────────────────────────────────────
_predict_fn = None
_model_spec = importlib.util.find_spec("models.sentiment_model")
if _model_spec is not None:
    from models.sentiment_model import predict as _predict_fn  # type: ignore

# ── Helper ────────────────────────────────────────────────────────────────────
def analyze_sentiment(feedback: str) -> str:
    """Return Positive / Neutral / Negative for a feedback string."""
    if _predict_fn is not None:
        result = _predict_fn(feedback)
        return result[0]['label']

    polarity = TextBlob(feedback).sentiment.polarity
    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    return "Neutral"

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usn      = request.form['usn']
        password = generate_password_hash(request.form['password'])

        conn   = sqlite3.connect('feedback.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students(usn, password) VALUES (?, ?)",
            (usn, password)
        )
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usn      = request.form['usn']
        password = request.form['password']

        conn   = sqlite3.connect('feedback.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM students WHERE usn=?", (usn,))
        data = cursor.fetchone()
        conn.close()                          # was missing in original

        if data and check_password_hash(data[0], password):
            return redirect('/')

    return render_template('login.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin123":
            return redirect('/dashboard')

    return render_template('admin_login.html')


@app.route('/dashboard')
def dashboard():
    conn   = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feedback")
    feedbacks = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', feedbacks=feedbacks)


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    """Receive a feedback form submission, store it, and e-mail the admin."""
    feedback  = request.form.get('feedback', '').strip()
    sentiment = analyze_sentiment(feedback)

    conn   = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feedback(feedback, sentiment) VALUES (?, ?)",
        (feedback, sentiment)
    )
    conn.commit()
    conn.close()

    # Non-blocking e-mail notification
    try:
        msg      = Message('New Feedback', recipients=['admin@gmail.com'])
        msg.body = f"New feedback submitted:\n\n{feedback}\n\nSentiment: {sentiment}"
        mail.send(msg)
    except Exception as e:
        print(f"Email sending failed: {e}")

    return redirect('/')


@app.route('/chart')
def chart():
    conn   = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute("SELECT feedback FROM feedback")
    rows = cursor.fetchall()
    conn.close()

    sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for row in rows:
        sentiments[analyze_sentiment(row[0])] += 1

    plt.figure()
    plt.bar(sentiments.keys(), sentiments.values(), color=['green', 'gray', 'red'])
    plt.title('Feedback Sentiment')
    plt.savefig('static/images/chart.png')
    plt.close()

    return redirect('/dashboard')


@app.route('/wordcloud')
def wordcloud():
    conn   = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute("SELECT feedback FROM feedback")
    rows = cursor.fetchall()
    conn.close()

    text = " ".join(row[0] for row in rows if row[0])
    wc   = WordCloud(width=800, height=400, background_color='white').generate(text)
    wc.to_file('static/images/wordcloud.png')

    return redirect('/dashboard')


@app.route('/csv')
def csv():
    conn = sqlite3.connect('feedback.db')
    df   = pd.read_sql_query("SELECT * FROM feedback", conn)
    conn.close()

    df.to_csv('reports/feedback.csv', index=False)
    return send_file('reports/feedback.csv', as_attachment=True)


@app.route('/pdf')
def pdf():
    if _canvas is None:
        return (
            "PDF generation library not available. "
            "Add 'reportlab' to requirements.txt to enable this feature.",
            503
        )

    c = _canvas.Canvas('reports/report.pdf')
    c.drawString(100, 800, "College Feedback Report")
    c.save()

    return send_file('reports/report.pdf', as_attachment=True)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
