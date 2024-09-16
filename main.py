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
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager

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
ma = Marshmallow(app)
jwt = JWTManager(app)
socketio = SocketIO(app)

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        socketio.emit('user_online', {'user_id': current_user.id, 'username': current_user.username}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        socketio.emit('user_offline', {'user_id': current_user.id, 'username': current_user.username}, broadcast=True)

# Import routes after initializing app to avoid circular imports
from routes import *

if __name__ == '__main__':
    logger.info("Starting Flask app...")
    try:
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Contents of current directory: {os.listdir()}")
        
        logger.info("Database tables created successfully")
        
        logger.info("Attempting to start Flask app on port 5000")
        logger.info(f"App instance: {app}")
        logger.info(f"SocketIO instance: {socketio}")

        with app.app_context():
            db.create_all()
            app.run(debug=True)

        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"An error occurred while starting the Flask app: {str(e)}")
        logger.error("Exception details:", exc_info=True)
        sys.exit(1)
