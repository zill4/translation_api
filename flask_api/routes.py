from flask import jsonify, request
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
from flask_login import login_user, logout_user
from translation_service import TranslationServiceClient
from sqlalchemy import or_

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

    # User Routes
    @api.route('/users')
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

    @api.route('/users/<int:user_id>')
    class UserDetail(Resource):
        @api.doc(security='jwt')
        @jwt_required()
        def get(self, user_id):
            """Get a user by ID"""
            user = User.query.get_or_404(user_id)
            return user_schema.jsonify(user)

        @api.doc(security='jwt')
        @jwt_required()
        @api.expect(user_model)
        def put(self, user_id):
            """Update a user"""
            data = request.get_json()
            user = User.query.get_or_404(user_id)

            if user.id != get_jwt_identity():
                return {"message": "Unauthorized"}, 403

            user.username = data.get('username', user.username)
            user.email = data.get('email', user.email)
            user.language = data.get('language', user.language)
            user.dialect = data.get('dialect', user.dialect)
            user.location = data.get('location', user.location)
            user.profile_picture = data.get('profile_picture', user.profile_picture)
            db.session.commit()
            return user_schema.jsonify(user)

        @api.doc(security='jwt')
        @jwt_required()
        def delete(self, user_id):
            """Delete a user"""
            user = User.query.get_or_404(user_id)

            if user.id != get_jwt_identity():
                return {"message": "Unauthorized"}, 403

            db.session.delete(user)
            db.session.commit()
            return {"message": "User deleted"}

    # Authentication Routes
    @api.route('/login')
    class Login(Resource):
        @api.expect(api.model('Login', {
            'username': fields.String(required=True),
            'password': fields.String(required=True)
        }))
        def post(self):
            """User login"""
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                access_token = create_access_token(identity=user.id)
                return {"access_token": access_token}, 200

            return {"message": "Invalid credentials"}, 401

    @api.route('/logout')
    class Logout(Resource):
        @api.doc(security='jwt')
        @jwt_required()
        def post(self):
            """User logout"""
            logout_user()
            return {"message": "Logged out successfully"}

    # Contacts Routes
    @api.route('/contacts')
    class ContactList(Resource):
        @api.doc(security='jwt')
        @jwt_required()
        def post(self):
            """Create a new contact"""
            data = request.get_json()
            contact_username = data.get('username', '').strip()
            user_id = get_jwt_identity()

            contact_user = User.query.filter_by(username=contact_username).first()
            if not contact_user:
                return {"message": "User not found"}, 404

            existing_contact = Contact.query.filter_by(owner_id=user_id, contact_id=contact_user.id).first()
            if existing_contact:
                return {"message": "Contact already exists"}, 400

            new_contact = Contact(owner_id=user_id, contact_id=contact_user.id)
            db.session.add(new_contact)
            db.session.commit()

            return contact_schema.jsonify(new_contact), 201

        @api.doc(security='jwt')
        @jwt_required()
        def get(self):
            """Get all contacts for the current user"""
            user_id = get_jwt_identity()
            contacts = Contact.query.filter_by(owner_id=user_id).all()
            return contacts_schema.jsonify(contacts)

    @api.route('/contacts/<int:contact_id>')
    class ContactDetail(Resource):
        @api.doc(security='jwt')
        @jwt_required()
        def delete(self, contact_id):
            """Delete a contact"""
            user_id = get_jwt_identity()
            contact = Contact.query.filter_by(owner_id=user_id, contact_id=contact_id).first_or_404()

            db.session.delete(contact)
            db.session.commit()
            return {"message": "Contact deleted"}

    # Messages Routes
    @api.route('/messages')
    class MessageList(Resource):
        @api.doc(security='jwt')
        @jwt_required()
        def post(self):
            """Create a new message"""
            data = request.get_json()
            sender_id = get_jwt_identity()
            receiver_id = data.get('receiver_id')
            content = data.get('content')

            message = Message(sender_id=sender_id, receiver_id=receiver_id)
            message.encrypt_content(content)
            db.session.add(message)
            db.session.commit()

            translated_content = translation_client.translate(content, 'en')
            message.translated_content = translated_content
            message.translated = True
            db.session.commit()

            socketio.emit('receive_message', message_schema.dump(message), room=str(receiver_id))

            return message_schema.jsonify(message), 201

        @api.doc(security='jwt')
        @jwt_required()
        def get(self):
            """Get messages for a specific contact"""
            user_id = get_jwt_identity()
            contact_id = request.args.get('contact_id', type=int)
            if not contact_id:
                return {"message": "Contact ID required"}, 400

            messages = Message.query.filter(
                ((Message.sender_id == user_id) & (Message.receiver_id == contact_id)) |
                ((Message.sender_id == contact_id) & (Message.receiver_id == user_id))
            ).order_by(Message.timestamp.asc()).all()

            for msg in messages:
                msg.content = msg.decrypt_content()

            return messages_schema.jsonify(messages)

    @api.route('/messages/<int:message_id>')
    class MessageDetail(Resource):
        @api.doc(security='jwt')
        @jwt_required()
        def get(self, message_id):
            """Get a specific message"""
            message = Message.query.get_or_404(message_id)
            message.content = message.decrypt_content()
            return message_schema.jsonify(message)

        @api.doc(security='jwt')
        @jwt_required()
        def delete(self, message_id):
            """Delete a message"""
            user_id = get_jwt_identity()
            message = Message.query.get_or_404(message_id)

            if message.sender_id != user_id:
                return {"message": "Unauthorized"}, 403

            db.session.delete(message)
            db.session.commit()
            return {"message": "Message deleted"}

    # User Settings Routes
    @api.route('/settings')
    class UserSettings(Resource):
        @api.doc(security='jwt')
        @jwt_required()
        def get(self):
            """Get user settings"""
            user_id = get_jwt_identity()
            user = User.query.get_or_404(user_id)
            return user_schema.jsonify(user)

        @api.doc(security='jwt')
        @jwt_required()
        @api.expect(user_model)
        def put(self):
            """Update user settings"""
            user_id = get_jwt_identity()
            user = User.query.get_or_404(user_id)

            data = request.get_json()
            user.language = data.get('language', user.language)
            user.dialect = data.get('dialect', user.dialect)
            user.location = data.get('location', user.location)
            user.profile_picture = data.get('profile_picture', user.profile_picture)
            db.session.commit()
            return user_schema.jsonify(user)

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

        translated_content = translation_client.translate(content, 'en')
        message.translated_content = translated_content
        message.translated = True
        db.session.commit()

        emit('receive_message', message_schema.dump(message), room=str(receiver_id))

    # Add resources to API
    api.add_resource(UserResource, '/api/users')
    api.add_resource(UserDetail, '/api/users/<int:user_id>')
    api.add_resource(Login, '/api/login')
    api.add_resource(Logout, '/api/logout')
    api.add_resource(ContactList, '/api/contacts')
    api.add_resource(ContactDetail, '/api/contacts/<int:contact_id>')
    api.add_resource(MessageList, '/api/messages')
    api.add_resource(MessageDetail, '/api/messages/<int:message_id>')
    api.add_resource(UserSettings, '/api/settings')