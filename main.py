from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO
from urllib.parse import urlparse
import logging
import sys
import os
from config import Config
from database import db
from models import User, Message
from translation_service import translation_service
from utils import detect_language
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load env var
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add a file handler to log to a file
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
socketio = SocketIO(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        language = request.form.get('language')
        dialect = request.form.get('dialect')

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.')
            return redirect(url_for('register'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, language=language, dialect=dialect)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    content = request.json.get('content')
    receiver_id = request.json.get('receiver_id')
    
    if not content or not receiver_id:
        return jsonify({"status": "error", "message": "Missing content or receiver_id"}), 400
    
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({"status": "error", "message": "Receiver not found"}), 404
    
    source_lang, source_dialect = detect_language(content)
    translated_content = translation_service.translate(
        content, 
        source_lang, 
        source_dialect, 
        receiver.language, 
        receiver.dialect
    )['translated_text']
    
    new_message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content,
        translated_content=translated_content,
        original_language=source_lang,
        original_dialect=source_dialect
    )
    db.session.add(new_message)
    db.session.commit()
    
    socketio.emit('new_message', {
        'sender': current_user.username,
        'content': translated_content
    }, room=receiver_id)
    
    return jsonify({"status": "success", "message": "Message sent successfully"})

@app.route('/get_messages')
@login_required
def get_messages():
    messages = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).order_by(Message.timestamp.asc()).all()
    
    message_list = []
    for message in messages:
        message_list.append({
            'sender': User.query.get(message.sender_id).username,
            'content': message.translated_content if message.receiver_id == current_user.id else message.content,
            'timestamp': message.timestamp.isoformat()
        })
    
    return jsonify(message_list)

@app.route('/get_users')
@login_required
def get_users():
    users = User.query.filter(User.id != current_user.id).all()
    user_list = [{'id': user.id, 'username': user.username} for user in users]
    return jsonify(user_list)

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        socketio.emit('user_online', {'user_id': current_user.id, 'username': current_user.username}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        socketio.emit('user_offline', {'user_id': current_user.id, 'username': current_user.username}, broadcast=True)

def create_app():
    with app.app_context():
        db.create_all()
    return app

if __name__ == '__main__':
    logger.info("Starting Flask app...")
    try:
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Contents of current directory: {os.listdir()}")
        
        create_app()
        logger.info("Database tables created successfully")
        
        logger.info("Attempting to start Flask app on port 5000")
        logger.info(f"App instance: {app}")
        logger.info(f"SocketIO instance: {socketio}")
        
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"An error occurred while starting the Flask app: {str(e)}")
        logger.error("Exception details:", exc_info=True)
        sys.exit(1)
