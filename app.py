from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# DATABASE CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///issues.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ISSUE TABLE
class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    images = db.Column(db.Text)
    status = db.Column(db.String(20), default='Reported')
    spam_count = db.Column(db.Integer, default=0)
    escalated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ✅ CREATE DATABASE TABLES
with app.app_context():
    db.create_all()

# ROUTES

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['description']
        category = request.form['category']
        lat = request.form['lat']
        lng = request.form['lng']

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return "Location access failed. Please allow GPS in your browser.", 400

        # Handle image upload
        files = request.files.getlist('images')
        filenames = []
        for file in files:
            if file and file.filename:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)
                filenames.append(file.filename)

        # Save issue
        issue = Issue(
            title=title,
            description=desc,
            category=category,
            lat=lat,
            lng=lng,
            images=','.join(filenames)
        )
        db.session.add(issue)
        db.session.commit()
        return redirect(url_for('home'))

    return render_template('report.html')

@app.route('/map')
def show_map():
    issues = Issue.query.filter(Issue.spam_count < 3).all()
    issue_data = []
    for i in issues:
        issue_data.append({
            "id": i.id,
            "title": i.title,
            "description": i.description,
            "category": i.category,
            "lat": i.lat,
            "lng": i.lng,
            "images": i.images,
            "escalated": i.escalated,
            "status": i.status
        })
    return render_template('map.html', issues=issue_data)

@app.route('/update_status/<int:issue_id>', methods=['POST'])
def update_status(issue_id):
    data = request.get_json()
    new_status = data['status']
    issue = Issue.query.get_or_404(issue_id)
    issue.status = new_status
    db.session.commit()
    return jsonify({"message": "Status updated"})

@app.route('/report_spam/<int:issue_id>', methods=['POST'])
def report_spam(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    issue.spam_count += 1
    db.session.commit()
    return jsonify({"message": "Spam reported", "count": issue.spam_count})

@app.route('/run_escalation')
def run_escalation():
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    issues = Issue.query.filter(Issue.created_at <= one_week_ago, Issue.status != 'Resolved', Issue.escalated == False).all()

    for issue in issues:
        issue.escalated = True

    db.session.commit()
    return jsonify({"message": f"{len(issues)} issues escalated."})

# ✅ Run app
if __name__ == '__main__':
    app.run(debug=True)
