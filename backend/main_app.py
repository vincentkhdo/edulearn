from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import logging

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

# Configure the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://edulearn_user:password@localhost/edulearn'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)

# Import and register blueprints
from app import main_blueprint

app.register_blueprint(main_blueprint)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
