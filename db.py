import mysql.connector
from flask_sqlalchemy import SQLAlchemy
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root3306',          # your MySQL username
    'password': 'sandraisabel022506_',  # your MySQL password
    'database': 'alday_dental'
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)