import os
import random
import time
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from groq import Groq
from dotenv import load_dotenv
import markdown

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=1)
    completed_nodes = db.Column(db.Text, default="[]") # JSON string of list

    def get_completed_nodes(self):
        try:
            return json.loads(self.completed_nodes)
        except:
            return []

    def add_completed_node(self, node_id):
        nodes = self.get_completed_nodes()
        if node_id not in nodes:
            nodes.append(node_id)
            self.completed_nodes = json.dumps(nodes)
            self.xp += 50 # Add XP
            db.session.commit()
            return True
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Data ---
ROADMAP_LEVELS = [
    {
        "id": "beginner",
        "title": "Beginner ML",
        "nodes": [
            {"id": "intro", "title": "What is AI?", "description": "Start your journey here."},
            {"id": "linear_regression", "title": "Linear Regression", "description": "Predicting numbers with lines."},
            {"id": "logistic_regression", "title": "Logistic Regression", "description": "Classifying things."},
            {"id": "gradient_descent", "title": "Gradient Descent", "description": "Ideally walking down a hill."}
        ]
    },
    {
        "id": "intermediate",
        "title": "Intermediate ML",
        "nodes": [
            {"id": "decision_trees", "title": "Decision Trees", "description": "Making choices."},
            {"id": "random_forest", "title": "Ensemble Methods", "description": "Strength in numbers."},
            {"id": "svm", "title": "Support Vector Machines", "description": "Drawing better lines."}
        ]
    },
    {
        "id": "advanced",
        "title": "Deep Learning",
        "nodes": [
            {"id": "neural_networks", "title": "Neural Networks", "description": "Brain-inspired computing."},
            {"id": "cnns", "title": "CNNs", "description": "Computer Vision."},
            {"id": "rnns", "title": "RNNs / LSTMs", "description": "Sequence data."}
        ]
    },
    {
        "id": "expert",
        "title": "ML Engineer",
        "nodes": [
            {"id": "transformers", "title": "Transformers", "description": "Current SOTA."},
            {"id": "deployment", "title": "Deployment", "description": "Shipping models."},
            {"id": "evaluation", "title": "Model Evaluation", "description": "Is it good?"}
        ]
    }
]

# --- Routes ---

@app.route('/')
@login_required
def index():
    user_completed = current_user.get_completed_nodes()
    return render_template('index.html', roadmap=ROADMAP_LEVELS, user=current_user, completed_nodes=user_completed)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login Failed. Check your username and password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'error')
            return redirect(url_for('signup'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/generate', methods=['POST'])
@login_required
def generate_content():
    data = request.json
    node_title = data.get('node_title')
    mode = data.get('mode')
    
    if not node_title or not mode:
        return jsonify({"error": "Missing node_title or mode"}), 400

    prompt = ""
    if mode == 'eli5':
        prompt = f"Explain the Machine Learning concept '{node_title}' to a 12-year-old. Use fun analogies (like cooking, sports, or video games). Keep it short, engaging, and inspiring."
    elif mode == 'theory':
        prompt = f"Explain the deep mathematical theory behind '{node_title}'. Include key algorithms, assumptions, and formulas (use LaTeX formatting where possible, e.g., $y = mx + b$). Be rigorous but clear."
    elif mode == 'code':
        prompt = f"Generate a Python code snippet using scikit-learn or PyTorch/TensorFlow to demonstrate '{node_title}'. Include comments explaining each step. The code should be self-contained and runnable."
    elif mode == 'visual':
        prompt = f"Describe a visual analogy or diagram that explains '{node_title}'. Be descriptive so a user can visualize it. Also, suggest a prompt for an image generator."
    elif mode == 'audio':
         prompt = f"Write a short, conversational script (like a podcast host) explaining '{node_title}'. Keep it under 2 minutes of reading time. Make it sound enthusiastic."
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a world-class AI educator. Your goal is to make ML joyful, clear, and inspiring."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024,
        )
        content = completion.choices[0].message.content
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/complete_node', methods=['POST'])
@login_required
def complete_node():
    data = request.json
    node_id = data.get('node_id')
    if node_id:
        if current_user.add_completed_node(node_id):
            return jsonify({"success": True, "xp": current_user.xp, "message": "XP Added!"})
        else:
            return jsonify({"success": True, "xp": current_user.xp, "message": "Already completed."})
    return jsonify({"error": "Missing node_id"}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
