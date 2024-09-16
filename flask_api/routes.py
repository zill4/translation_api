from flask import jsonify, request
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from models import User, Message
from schemas import user_schema, users_schema, message_schema, messages_schema
from database import db
from main import app

@app.route('/api/register', methods=['POST'])
def register():
    username = request.json.get('username')
    email = request.json.get('email')
    password = request.json.get('password')
    
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists"}), 400
    
    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User created successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/messages', methods=['POST'])
@jwt_required()
def send_message():
    content = request.json.get('content')
    receiver_id = request.json.get('receiver_id')
    sender_id = get_jwt_identity()
    
    new_message = Message(content=content, sender_id=sender_id, receiver_id=receiver_id)
    db.session.add(new_message)
    db.session.commit()
    
    return jsonify(message_schema.dump(new_message)), 201

@app.route('/api/messages', methods=['GET'])
@jwt_required()
def get_messages():
    user_id = get_jwt_identity()
    messages = Message.query.filter((Message.sender_id == user_id) | (Message.receiver_id == user_id)).all()
    return jsonify(messages_schema.dump(messages)), 200

@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    users = User.query.all()
    return jsonify(users_schema.dump(users)), 200