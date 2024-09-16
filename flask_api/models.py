from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from cryptography.fernet import Fernet

# Generate a key for encryption (Store this securely)
encryption_key = Fernet.generate_key()
cipher_suite = Fernet(encryption_key)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    language = db.Column(db.String(10), default='en')
    contacts = db.relationship('Contact', backref='owner', lazy='dynamic')
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    contact_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    contact = db.relationship('User', foreign_keys=[contact_id])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_encrypted = db.Column(db.LargeBinary, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    translated = db.Column(db.Boolean, default=False)
    translated_content = db.Column(db.Text)

    def encrypt_content(self, content):
        self.content_encrypted = cipher_suite.encrypt(content.encode())

    def decrypt_content(self):
        return cipher_suite.decrypt(self.content_encrypted).decode()