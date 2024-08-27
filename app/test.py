
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

john = NODE(label='Person',properties={'age':10
                                       ,'location':'Pittsburg'
                                       ,"created_at": "2024-08-25"
                                       ,'name':'john'})

alex = NODE(label='Person',properties={'age':10
                                       ,'location':'Pittsburg'
                                       ,"created_at": "2024-08-25"
                                       ,'name':'alex'})

for n in [john,alex]:
    n.create_or_update(driver)

alex.create_or_update_relationship(driver,john.uuid, relationship_type='FRIEND',properties={'Years':2})



NewUser = User(username='BigJohn',properties={'email':'bj@ggg.com'})
NewUser.register(driver,password='MyPass')

NewUser.create_world(driver,world_name='NewtonWorld',world_properties={'pop_limit':10000})

first_world_data = NewUser.get_worlds(driver)[0]
# Create a World object using the data from the first world
FirstWorld = World(
    uuid=first_world_data["uuid"]
)
FirstWorld.create_or_update_node(driver,node_label='Character',node_properties={'name':'Johnny'})