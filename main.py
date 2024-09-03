from flask import Flask
from neo4j import GraphDatabase
import os
from app.routes import create_app_routes  # Importing routes from the app folder
from app.utils import wipe_neo4j_database

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize the Neo4j driver
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(username, password))
#wipe database
#wipe_neo4j_database(driver)

# Create and configure the Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Register the routes with the driver passed in
app.register_blueprint(create_app_routes(driver))

if __name__ == '__main__':
    app.run(debug=True,port=5001)