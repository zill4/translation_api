from app import ma
from models import User, Message, Contact

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        exclude = ('password_hash',)

class ContactSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Contact
        load_instance = True
        include_fk = True

class MessageSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Message
        load_instance = True
        include_fk = True

    sender = ma.Nested(UserSchema)
    receiver = ma.Nested(UserSchema)

user_schema = UserSchema()
users_schema = UserSchema(many=True)
contact_schema = ContactSchema()
contacts_schema = ContactSchema(many=True)
message_schema = MessageSchema()
messages_schema = MessageSchema(many=True)