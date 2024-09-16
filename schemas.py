from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from models import User, Message

class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        exclude = ('password_hash',)

class MessageSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Message
        load_instance = True

user_schema = UserSchema()
users_schema = UserSchema(many=True)
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)