from flask import Flask
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_marshmallow import Marshmallow

from config import Config
from database import db, migrate
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate.init_app(app, db)
ma = Marshmallow()
ma.init_app(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

login_manager = LoginManager()
login_manager.init_app(app)

# Import routes after initializing app to avoid circular imports
from routes import *

if __name__ == '__main__':
    print("Starting the Flask application")
    print("App listening on port 5000")
    socketio.run(app, host='0.0.0.0', port=5000)