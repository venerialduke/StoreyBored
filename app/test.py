
from neo4j import GraphDatabase
import os
import uuid
from utils import wipe_neo4j_database, NODE, User, World
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Neo4j connection setup
uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")


driver = GraphDatabase.driver(uri, auth=(username, password))

wipe_neo4j_database(driver)

NewUser = User(username='BigJohn',properties={'email':'bj@ggg.com'})
NewUser.register(driver,password='MyPass')

NewUser.create_world(driver,world_name='NewtonWorld',world_properties={'pop_limit':10000})

first_world_data = NewUser.get_worlds(driver)[0]
# Instantiate a World object using the data from the first world
FirstWorld = World(
    uuid=first_world_data["uuid"],  # The UUID is required separately to identify the node in the database
    properties=first_world_data     # The entire properties dictionary is passed, which includes name, uuid, etc.
)
print(f"World Population Limit: {FirstWorld.properties['pop_limit']}")
FirstWorld.create_or_update_node(
    driver,
    node_label='Character',
    node_properties={'name': 'Johnny'}
)