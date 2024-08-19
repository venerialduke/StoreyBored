from flask import Flask
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from flask_login import LoginManager
from app.models import User  # Import the User class

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Neo4j connection setup
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(uri, auth=(username, password))

@app.teardown_appcontext
def close_driver(exception):
    if driver:
        driver.close()

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    with driver.session() as session:
        result = session.run(
            "MATCH (u:User) WHERE ID(u) = $user_id RETURN u",
            user_id=int(user_id)
        )
        user_data = result.single()
        if user_data:
            user_node = user_data['u']
            return User.from_node(user_node)
        return None

from app import routes