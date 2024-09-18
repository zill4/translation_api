from flask import Flask
from config import Config
from extensions import db, ma, migrate, jwt, login_manager, socketio
from models import User, Message, Contact
from routes import register_routes
import eventlet

eventlet.monkey_patch()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')

    # Register routes
    register_routes(app)

    return app

app = create_app()

if __name__ == '__main__':
    print("Starting the Flask application")
    print("App listening on port 5001")
    socketio.run(app, host='0.0.0.0', port=5001)