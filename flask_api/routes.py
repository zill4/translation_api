from flask import jsonify, request, current_app
from flask_restx import Api, Resource, fields
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from models import User, Message, Contact
from schemas import (
    user_schema, users_schema,
    contact_schema, contacts_schema,
    message_schema, messages_schema
)
from extensions import db, socketio, login_manager
from flask_socketio import emit, join_room
from flask_login import login_user, logout_user, current_user, login_required
from translation_service import TranslationServiceClient
from sqlalchemy import or_
import os

translation_client = TranslationServiceClient()

def register_routes(app, api):
    # Define API models
    user_model = api.model('User', {
        'username': fields.String(required=True, description='User username'),
        'email': fields.String(required=True, description='User email'),
        'password': fields.String(required=True, description='User password'),
        'language': fields.String(description='User preferred language'),
        'dialect': fields.String(description='User preferred dialect'),
        'location': fields.String(description='User location'),
        'profile_picture': fields.String(description='User profile picture URL')
    })

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # User CRUD Routes
    @api.route('/api/users')
    class UserResource(Resource):
        @api.expect(user_model)
        @api.response(201, 'User created successfully')
        @api.response(400, 'Username or email already exists')
        def post(self):
            """Create a new user"""
            data = request.get_json()
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()

            if User.query.filter(or_(User.username == username, User.email == email)).first():
                return {"message": "Username or email already exists"}, 400

            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            access_token = create_access_token(identity=new_user.id)
            return {"access_token": access_token}, 201

    @app.route('/api/users/<int:user_id>', methods=['GET'])
    @jwt_required()
    def get_user(user_id):
        user = User.query.get_or_404(user_id)
        return user_schema.jsonify(user), 200

    @app.route('/api/users/<int:user_id>', methods=['PUT'])
    @jwt_required()
    def update_user(user_id):
        data = request.get_json()
        user = User.query.get_or_404(user_id)

        if user.id != get_jwt_identity():
            return jsonify({"message": "Unauthorized"}), 403

        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.language = data.get('language', user.language)
        user.dialect = data.get('dialect', user.dialect)
        user.location = data.get('location', user.location)
        user.profile_picture = data.get('profile_picture', user.profile_picture)
        db.session.commit()
        return user_schema.jsonify(user), 200

    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    @jwt_required()
    def delete_user(user_id):
        user = User.query.get_or_404(user_id)

        if user.id != get_jwt_identity():
            return jsonify({"message": "Unauthorized"}), 403

        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted"}), 200

    # Authentication Routes

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

    # Contacts CRUD Routes

    @app.route('/api/contacts', methods=['POST'])
    @jwt_required()
    def create_contact():
        data = request.get_json()
        contact_username = data.get('username', '').strip()
        user_id = get_jwt_identity()

        contact_user = User.query.filter_by(username=contact_username).first()
        if not contact_user:
            return jsonify({"message": "User not found"}), 404

        existing_contact = Contact.query.filter_by(owner_id=user_id, contact_id=contact_user.id).first()
        if existing_contact:
            return jsonify({"message": "Contact already exists"}), 400

        new_contact = Contact(owner_id=user_id, contact_id=contact_user.id)
        db.session.add(new_contact)
        db.session.commit()

        return contact_schema.jsonify(new_contact), 201

    @app.route('/api/contacts', methods=['GET'])
    @jwt_required()
    def get_contacts():
        user_id = get_jwt_identity()
        contacts = Contact.query.filter_by(owner_id=user_id).all()
        return contacts_schema.jsonify(contacts), 200

    @app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
    @jwt_required()
    def delete_contact(contact_id):
        user_id = get_jwt_identity()
        contact = Contact.query.filter_by(owner_id=user_id, contact_id=contact_id).first_or_404()

        db.session.delete(contact)
        db.session.commit()
        return jsonify({"message": "Contact deleted"}), 200

    # Messages CRUD Routes

    @app.route('/api/messages', methods=['POST'])
    @jwt_required()
    def create_message():
        data = request.get_json()
        sender_id = get_jwt_identity()
        receiver_id = data.get('receiver_id')
        content = data.get('content')

        message = Message(sender_id=sender_id, receiver_id=receiver_id)
        message.encrypt_content(content)
        db.session.add(message)
        db.session.commit()

        # Translate the message asynchronously
        # ... Translation logic here ...
        translated_content = translation_client.translate(content, 'en')  # Example: translating to English
        message.translated_content = translated_content
        message.translated = True
        db.session.commit()
        # Emit the message to the receiver's room
        socketio.emit('receive_message', message_schema.dump(message), room=str(receiver_id))

        return message_schema.jsonify(message), 201

    @app.route('/api/messages/<int:message_id>', methods=['GET'])
    @jwt_required()
    def get_message(message_id):
        message = Message.query.get_or_404(message_id)
        # Decrypt message before sending
        message.content = message.decrypt_content()
        return message_schema.jsonify(message), 200

    @app.route('/api/messages', methods=['GET'])
    @jwt_required()
    def get_messages():
        user_id = get_jwt_identity()
        contact_id = request.args.get('contact_id', type=int)
        if not contact_id:
            return jsonify({"message": "Contact ID required"}), 400

        messages = Message.query.filter(
            ((Message.sender_id == user_id) & (Message.receiver_id == contact_id)) |
            ((Message.sender_id == contact_id) & (Message.receiver_id == user_id))
        ).order_by(Message.timestamp.asc()).all()

        # Decrypt messages before sending
        for msg in messages:
            msg.content = msg.decrypt_content()

        return messages_schema.jsonify(messages), 200

    @app.route('/api/messages/<int:message_id>', methods=['DELETE'])
    @jwt_required()
    def delete_message(message_id):
        user_id = get_jwt_identity()
        message = Message.query.get_or_404(message_id)

        if message.sender_id != user_id:
            return jsonify({"message": "Unauthorized"}), 403

        db.session.delete(message)
        db.session.commit()
        return jsonify({"message": "Message deleted"}), 200

    # User Settings Routes

    @app.route('/api/settings', methods=['PUT'])
    @jwt_required()
    def update_settings():
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)

        data = request.get_json()
        user.language = data.get('language', user.language)
        user.dialect = data.get('dialect', user.dialect)
        user.location = data.get('location', user.location)
        user.profile_picture = data.get('profile_picture', user.profile_picture)
        db.session.commit()
        return user_schema.jsonify(user), 200

    @app.route('/api/settings', methods=['GET'])
    @jwt_required()
    def get_settings():
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        return user_schema.jsonify(user), 200
    api.add_resource(UserResource, '/api/users')

    # SocketIO Events

    @socketio.on('connect')
    @jwt_required()
    def connect():
        user_id = get_jwt_identity()
        join_room(str(user_id))
        emit('status', {'message': f'User {user_id} has joined the room.'}, room=str(user_id))

    @socketio.on('send_message')
    @jwt_required()
    def handle_send_message(data):
        sender_id = get_jwt_identity()
        receiver_id = data.get('receiver_id')
        content = data.get('content')

        message = Message(sender_id=sender_id, receiver_id=receiver_id)
        message.encrypt_content(content)
        db.session.add(message)
        db.session.commit()

        # Translation logic can be added here
    # Translate the message asynchronously
        translated_content = translation_client.translate(content, 'en')  # Example: translating to English
        message.translated_content = translated_content
        message.translated = True
        db.session.commit()
        # Emit the message to the receiver's room
        emit('receive_message', message_schema.dump(message), room=str(receiver_id))
    
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
    # ... Additional routes and logic as needed ...