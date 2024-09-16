from marshmallow import Schema, fields
from models import User, Message, Contact

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    language = fields.Str()
    dialect = fields.Str()
    location = fields.Str()
    profile_picture = fields.Str()

class ContactSchema(Schema):
    id = fields.Int(dump_only=True)
    owner_id = fields.Int(required=True)
    contact_id = fields.Int(required=True)

class MessageSchema(Schema):
    id = fields.Int(dump_only=True)
    sender_id = fields.Int(required=True)
    receiver_id = fields.Int(required=True)
    content = fields.Str(required=True)  # We'll handle encryption/decryption in the model
    timestamp = fields.DateTime(dump_only=True)
    translated = fields.Boolean()
    translated_content = fields.Str()


user_schema = UserSchema()
users_schema = UserSchema(many=True)
contact_schema = ContactSchema()
contacts_schema = ContactSchema(many=True)
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)