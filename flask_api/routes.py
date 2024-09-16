from flask import jsonify, request
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from models import User, Message, Contact
from schemas import user_schema, message_schema, messages_schema, contact_schema, contacts_schema
from database import db
from flask_socketio import emit, join_room
from flask_login import login_user, logout_user
from app import app, socketio
from translation_service import TranslationServiceClient
# from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

# login_manager = LoginManager()
# login_manager.init_app(app)

translation_client = TranslationServiceClient()

@app.login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if User.query.filter(or_(User.username == username, User.email == email)).first():
        return jsonify({"message": "Username or email already exists"}), 400

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.id)
    return jsonify(access_token=access_token), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user)
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200

    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/api/add_contact', methods=['POST'])
@jwt_required()
def add_contact():
    data = request.get_json()
    contact_username = data.get('username', '').strip()
    user_id = get_jwt_identity()

    contact = User.query.filter_by(username=contact_username).first()
    if not contact:
        return jsonify({"message": "User not found"}), 404

    existing_contact = Contact.query.filter_by(owner_id=user_id, contact_id=contact.id).first()
    if existing_contact:
        return jsonify({"message": "Contact already added"}), 400

    new_contact = Contact(owner_id=user_id, contact_id=contact.id)
    db.session.add(new_contact)
    db.session.commit()

    return contact_schema.dump(new_contact), 201

@app.route('/api/contacts', methods=['GET'])
@jwt_required()
def get_contacts():
    user_id = get_jwt_identity()
    contacts = Contact.query.filter_by(owner_id=user_id).all()
    return jsonify(contacts_schema.dump(contacts)), 200

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = get_jwt_identity()
    receiver_id = data.get('receiver_id')
    content = data.get('content')

    # Encrypt the message
    message = Message(sender_id=sender_id, receiver_id=receiver_id)
    message.encrypt_content(content)
    db.session.add(message)
    db.session.commit()

    # Translate the message asynchronously
    translated_content = translation_client.translate(content, 'en')  # Example: translating to English
    message.translated_content = translated_content
    message.translated = True
    db.session.commit()

    # Emit the message to the receiver's room
    emit('receive_message', message_schema.dump(message), room=str(receiver_id))

@app.route('/api/messages/<int:contact_id>', methods=['GET'])
@jwt_required()
def get_messages(contact_id):
    user_id = get_jwt_identity()
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == contact_id)) |
        ((Message.sender_id == contact_id) & (Message.receiver_id == user_id))
    ).order_by(Message.timestamp.asc()).all()

    # Decrypt messages before sending
    for msg in messages:
        msg.content = msg.decrypt_content()

    return jsonify(messages_schema.dump(messages)), 200

@socketio.on('join')
def on_join(data):
    user_id = get_jwt_identity()
    join_room(str(user_id))

@app.route('/api/user/profile', methods=['GET', 'PUT'])
@jwt_required()
def user_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if request.method == 'GET':
        return user_schema.dump(user), 200
    elif request.method == 'PUT':
        data = request.get_json()
        user.language = data.get('language', user.language)
        db.session.commit()
        return user_schema.dump(user), 200