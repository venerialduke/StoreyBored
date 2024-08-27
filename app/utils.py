from neo4j import GraphDatabase
import uuid
from passlib.hash import bcrypt

def wipe_neo4j_database(driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

# Define a class that does generic Neo4j things on a Node
class NODE:
    def __init__(self, uuid=None, label=None, properties=None):
        self.uuid = uuid
        self.label = label
        self.properties = properties or {}

    def create_or_update(self, driver):
        with driver.session() as session:
            if self.uuid:
                # Update existing node
                query = f"""
                    MATCH (n:{self.label} {{uuid: $uuid}})
                    SET n += $properties
                """
                session.run(query, uuid=self.uuid, properties=self.properties)
            else:
                # Create new node
                self.uuid = str(uuid.uuid4())
                query = f"""
                    CREATE (n:{self.label} {{uuid: $uuid}})
                    SET n += $properties
                """
                session.run(query, uuid=self.uuid, properties=self.properties)

    def find_relationships(self, driver, relationship_type=None, unique_nodes=False):
        with driver.session() as session:
            if relationship_type:
                if isinstance(relationship_type, list):
                    # Multiple relationship types
                    relationship_types = '|'.join(relationship_type)
                    query = f"""
                        MATCH (n:{self.label} {{uuid: $uuid}})-[r:{relationship_types}]->(m)
                        RETURN r, m
                    """
                else:
                    # Single relationship type
                    query = f"""
                        MATCH (n:{self.label} {{uuid: $uuid}})-[r:{relationship_type}]->(m)
                        RETURN r, m
                    """
            else:
                # Any relationship type
                query = f"""
                    MATCH (n:{self.label} {{uuid: $uuid}})-[r]->(m)
                    RETURN r, m
                """
            result = session.run(query, uuid=self.uuid)
            relationships = [(record['r'], record['m']) for record in result]
            
            if unique_nodes:
                # Process relationships to extract unique nodes
                nodes = {node['uuid']: node for _, node in relationships}.values()
                return list(nodes)
            return relationships if relationships else None

    def create_or_update_relationship(self, driver, target_node_uuid, relationship_type, properties=None, direction=True):
        with driver.session() as session:
            if direction:
                # Directed relationship: node-[r]->targetnode
                query = f"""
                    MATCH (n:{self.label} {{uuid: $uuid}}), (m {{uuid: $target_node_uuid}})
                    MERGE (n)-[r:{relationship_type}]->(m)
                    SET r += $properties
                """
            else:
                # Undirected relationship: node-[r]-targetnode (without specifying direction)
                query = f"""
                    MATCH (n:{self.label} {{uuid: $uuid}}), (m {{uuid: $target_node_uuid}})
                    MERGE (n)-[r:{relationship_type}]-(m)
                    SET r += $properties
                """
            
            session.run(query, uuid=self.uuid, target_node_uuid=target_node_uuid, properties=properties or {})


class World(NODE):
    def __init__(self, uuid=None, name=None, properties=None):
        super().__init__(uuid=uuid, label="World", properties=properties)
        if name:
            self.properties["name"] = name

    def create_or_update_node(self, driver, node_label, node_properties, node_uuid=None, relationship_properties=None):
        # Create or update the NODE object
        node = NODE(uuid=node_uuid, label=node_label, properties=node_properties)
        node.create_or_update(driver)

        # Debug: Print confirmation that the node was created/updated
        print(f"Node created/updated: {node.uuid}")

        # Establish the "CONTAINS" relationship between the world and the node
        self.create_or_update_relationship(driver, target_node_uuid=node.uuid, relationship_type="CONTAINS", properties=relationship_properties)

        # Debug: Print confirmation that the relationship was created
        print(f"Relationship 'CONTAINS' created between World {self.uuid} and Node {node.uuid}")

        return node
    
    def get_nodes(self, driver, relationship_type="CONTAINS"):
        return self.find_relationships(driver, relationship_type=relationship_type, unique_nodes=True)




class User(NODE):
    def __init__(self, uuid=None, username=None, properties=None):
        super().__init__(uuid=uuid, label="User", properties=properties)
        if username:
            self.properties["username"] = username

    def find(self, driver):
        with driver.session() as session:
            result = session.run(
                "MATCH (u:User {username: $username}) RETURN u", 
                username=self.properties.get("username")
            )
            user_node = result.single()
            if user_node:
                self.uuid = user_node["u"]["uuid"]
                self.properties.update(user_node["u"])
            return user_node

    def register(self, driver, password):
        if not self.find(driver):
            # Hash the password
            hashed_password = bcrypt.hash(password)
            self.properties["password"] = hashed_password
            self.create_or_update(driver)
            return True
        else:
            return False

    def verify_password(self, driver, password):
        user = self.find(driver)
        if user:
            stored_password = self.properties.get("password")
            return bcrypt.verify(password, stored_password)
        else:
            return False
        

    def create_world(self, driver, world_name, world_properties=None):
        world_properties = world_properties or {}
        world = World(properties={"name": world_name, **world_properties})
        world.create_or_update(driver)
        self.create_or_update_relationship(driver, target_node_uuid=world.uuid, relationship_type="OWNS")
        return world
    
    def get_worlds(self, driver):
        return self.find_relationships(driver, relationship_type="OWNS", unique_nodes=True)
        
