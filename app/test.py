
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
FirstWorld = NODE.from_database(driver, uuid=first_world_data["uuid"])

print(f"World Population Limit: {FirstWorld.properties['pop_limit']}")

#Create some locations

location_list = [{'name':'Charlestown','population':100}
                 ,{'name':'Boston','population':1000}
                 ,{'name':'Seattle','population':2344}
                 ,{'name':'Windy City','population':544}
                 ,{'name':'Belltown','population':6}]

for location in location_list:
    FirstWorld.create_or_update_node(
        driver,
        node_label='Location',
        node_properties=location
    )

#Now create a list of locations from the database
charlestown = NODE.from_database(driver,FirstWorld.find_nodes_by_label_and_properties(driver,label='Location',properties={'name':'Charlestown'})[0]["uuid"])
seattle = NODE.from_database(driver,FirstWorld.find_nodes_by_label_and_properties(driver,label='Location',properties={'name':'Seattle'})[0]["uuid"])
boston = NODE.from_database(driver,FirstWorld.find_nodes_by_label_and_properties(driver,label='Location',properties={'name':'Boston'})[0]["uuid"])
windy_city = NODE.from_database(driver,FirstWorld.find_nodes_by_label_and_properties(driver,label='Location',properties={'name':'Windy City'})[0]["uuid"])
belltown = NODE.from_database(driver,FirstWorld.find_nodes_by_label_and_properties(driver,label='Location',properties={'name':'Belltown'})[0]["uuid"])



seattle.connect_to_location(driver,charlestown.uuid,path_properties={'name':'The Fast Road','rocks':10})
charlestown.connect_to_location(driver,seattle.uuid,path_properties={'name':'The Slow Road','rocks':100})
belltown.connect_to_location(driver,windy_city.uuid,path_properties={'name':'Jumpy Street','rocks':1})
belltown.connect_to_location(driver,seattle.uuid,path_properties={'name':'Cringe Street','rocks':1000})
boston.connect_to_location(driver,charlestown.uuid,path_properties={'name':'Cringe Street','rocks':560})
seattle.connect_to_location(driver,boston.uuid,path_properties={'name':'Cringe Street','rocks':25})

mypaths = boston.find_routes_to(driver,seattle.uuid,max_depth=5,criteria=None)
print(len(mypaths))