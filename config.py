import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    print("DATABASE URI")
    print(SQLALCHEMY_DATABASE_URI)
SQLALCHEMY_TRACK_MODIFICATIONS = False
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-string'