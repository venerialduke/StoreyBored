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

    @classmethod
    def from_database(cls, driver, uuid):
        with driver.session() as session:
            result = session.run("MATCH (n) WHERE n.uuid = $uuid RETURN labels(n) AS labels, n", uuid=uuid)
            record = result.single()

            if not record:
                raise ValueError(f"No node found with UUID {uuid}")

            labels = record["labels"]
            properties = dict(record["n"])

            if "User" in labels:
                return User(uuid=uuid, properties=properties)
            elif "World" in labels:
                return World(uuid=uuid, properties=properties)
            elif "Location" in labels:
                return Location(uuid=uuid, properties=properties)
            elif "Character" in labels:
                return Character(uuid=uuid, properties=properties)
            elif "Faction" in labels:
                return Faction(uuid=uuid, properties=properties)
            else:
                return NODE(uuid=uuid, label=labels[0], properties=properties)

    def create_or_update(self, driver):
        with driver.session() as session:
            if self.uuid:
                # Existing node: update properties
                query = f"""
                    MATCH (n {{uuid: $uuid}})
                    SET n += $properties
                    RETURN n
                """
                session.run(query, uuid=self.uuid, properties=self.properties)
            else:
                # New node: create with properties
                query = f"""
                    CREATE (n:{self.label} $properties)
                    SET n.uuid = $uuid
                    RETURN n
                """
                self.uuid = str(uuid.uuid4())
                session.run(query, uuid=self.uuid, properties=self.properties)

    def find_relationships(self, driver, relationship_type=None, unique_nodes=False, direction=True):
        with driver.session() as session:
            # Build the MATCH clause based on direction
            if direction:
                if relationship_type:
                    if isinstance(relationship_type, list):
                        # Multiple relationship types
                        relationship_types = '|'.join(relationship_type)
                        query = f"""
                            MATCH (n:{self.label} {{uuid: $uuid}})-[r:{relationship_types}]->(m)
                            RETURN r, m, labels(m) AS labels
                        """
                    else:
                        # Single relationship type
                        query = f"""
                            MATCH (n:{self.label} {{uuid: $uuid}})-[r:{relationship_type}]->(m)
                            RETURN r, m, labels(m) AS labels
                        """
                else:
                    # Any relationship type
                    query = f"""
                        MATCH (n:{self.label} {{uuid: $uuid}})-[r]->(m)
                        RETURN r, m, labels(m) AS labels
                    """
            else:
                if relationship_type:
                    if isinstance(relationship_type, list):
                        # Multiple relationship types
                        relationship_types = '|'.join(relationship_type)
                        query = f"""
                            MATCH (n:{self.label} {{uuid: $uuid}})-[r:{relationship_types}]-(m)
                            RETURN r, m, labels(m) AS labels
                        """
                    else:
                        # Single relationship type
                        query = f"""
                            MATCH (n:{self.label} {{uuid: $uuid}})-[r:{relationship_type}]-(m)
                            RETURN r, m, labels(m) AS labels
                        """
                else:
                    # Any relationship type
                    query = f"""
                        MATCH (n:{self.label} {{uuid: $uuid}})-[r]-(m)
                        RETURN r, m, labels(m) AS labels
                    """
            
            result = session.run(query, uuid=self.uuid)
            relationships = [(record['r'], record['m'], record['labels']) for record in result]
            
            if unique_nodes:
                # Process relationships to extract unique nodes and include labels
                nodes = {node['uuid']: {**node, 'labels': labels} for _, node, labels in relationships}.values()
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
        relationships = self.find_relationships(driver, relationship_type=relationship_type, unique_nodes=True)
        if relationships:
            nodes = []
            for node in relationships:
                # Ensure the node is a dictionary containing 'properties' and 'labels'
                nodes.append({
                    "properties": node,  # Assuming node itself is the properties dictionary
                    "labels": node["labels"]
                })
            return nodes
        return []
    
    # Method to find all nodes with a certain label
    def find_nodes_by_label(self, driver, label):
        with driver.session() as session:
            query = f"""
                MATCH (w:World {{uuid: $uuid}})-[:CONTAINS]->(n:{label})
                RETURN n
            """
            result = session.run(query, uuid=self.uuid)
            nodes = [record["n"] for record in result]
            return nodes if nodes else None

    def find_nodes_by_label_and_properties(self, driver, label, properties):
        with driver.session() as session:
            # Dynamically build the WHERE clause based on the properties
            conditions = [f"n.{key} = ${key}" for key in properties.keys()]
            query = f"""
                MATCH (w:World {{uuid: $uuid}})-[:CONTAINS]->(n:{label})
                WHERE {" AND ".join(conditions)}
                RETURN n
            """
            result = session.run(query, uuid=self.uuid, **properties)
            nodes = [record["n"] for record in result]
            return nodes if nodes else None

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

class Location(NODE):
    def __init__(self, uuid=None, properties=None):
        super().__init__(uuid=uuid, label="Location", properties=properties)

    # Method to add a character or object to the location
    def add_occupant(self, driver, occupant_uuid, properties=None):
        self.create_or_update_relationship(driver, target_node_uuid=occupant_uuid, relationship_type="OCCUPANT", properties=properties,direction=False)

    # Method to retrieve all occupants (e.g., characters or objects) at this location
    def get_occupants(self, driver):
        return self.find_relationships(driver, relationship_type="OCCUPANT", unique_nodes=True,direction=False)

    # Method to connect this location to another location via a route
    def connect_to_location(self, driver, other_location_uuid, route_properties=None):
        self.create_or_update_relationship(driver, target_node_uuid=other_location_uuid, relationship_type="ROUTE", properties=route_properties, direction=False)

    # Method to retrieve all routes connected to this location
    def get_routes(self, driver):
        return self.find_relationships(driver, relationship_type="ROUTE", unique_nodes=True, direction=False)
    
    def find_routes_to(self, driver, target_location_uuid, max_depth=5, criteria=None):
        criteria = criteria or {}
        with driver.session() as session:
            # Start building the Cypher query
            query = f"""
                MATCH p=(start:Location {{uuid: '{self.uuid}'}})-[:ROUTE*..{max_depth}]-(end:Location {{uuid: '{target_location_uuid}'}})
            """
            
            # Dynamically build the reduce functions for each criterion
            aggregates = []
            conditions = []
            for param, limits in criteria.items():
                aggregate = f"reduce(total_{param} = 0, rel in relationships(p) | total_{param} + coalesce(rel.{param}, 0)) AS total_{param}"
                aggregates.append(aggregate)
                if 'min' in limits:
                    conditions.append(f"total_{param} >= {limits['min']}")
                if 'max' in limits:
                    conditions.append(f"total_{param} <= {limits['max']}")
            
            # Add the WITH clause if there are aggregates
            if aggregates:
                query += " WITH p, " + ', '.join(aggregates)
            
            # Add the WHERE clause if there are conditions
            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"
            
            # Finally, return the path and total criteria values
            query += " RETURN p, " + ', '.join([f"total_{param}" for param in criteria.keys()])

            # Debug: Print the query
            print("Cypher Query:", query)

            # Execute the query
            result = session.run(query)
            
            paths = []
            for record in result:
                path = record["p"]
                nodes = [node["uuid"] for node in path.nodes]
                relationships = [{"start": rel.start_node["uuid"], "end": rel.end_node["uuid"], "type": type(rel).__name__} for rel in path.relationships]
                
                path_data = {"nodes": nodes, "relationships": relationships}
                for param in criteria.keys():
                    path_data[f"total_{param}"] = record.get(f"total_{param}", 0)
                
                paths.append(path_data)
            
            return paths if paths else None


class Character(NODE):
    def __init__(self, uuid=None, properties=None):
        super().__init__(uuid=uuid, label="Character", properties=properties)

    # Method to add the character to a faction
    def join_faction(self, driver, faction_uuid, properties=None, direction=False):
        self.create_or_update_relationship(driver, target_node_uuid=faction_uuid, relationship_type="MEMBER", properties=properties, direction=direction)

    # Method to add the character to a location
    def occupy_location(self, driver, location_uuid, properties=None, direction=False):
        self.create_or_update_relationship(driver, target_node_uuid=location_uuid, relationship_type="OCCUPANT", properties=properties, direction=direction)

    # Method to interact with another character
    def interact_with(self, driver, other_character_uuid, relationship_type="INTERACTS_WITH", properties=None,direction=True):
        self.create_or_update_relationship(driver, target_node_uuid=other_character_uuid, relationship_type=relationship_type, properties=properties,direction=direction)

    # Method to retrieve all factions this character belongs to
    def get_factions(self, driver):
        return self.find_relationships(driver, relationship_type="MEMBER", unique_nodes=True, direction=False)

    # Method to retrieve all locations this character occupies
    def get_locations(self, driver):
        return self.find_relationships(driver, relationship_type="OCCUPANT", unique_nodes=True, direction=False)

    # Method to retrieve all characters this character interacts with
    def get_interactions(self, driver, interaction_type=None):
        return self.find_relationships(driver, relationship_type=interaction_type or "INTERACTS_WITH", unique_nodes=True)
    
class Faction(NODE):
    def __init__(self, uuid=None, properties=None):
        super().__init__(uuid=uuid, label="Faction", properties=properties)

    # Method to add a member (character) to the faction
    def add_member(self, driver, character_uuid, properties=None):
        self.create_or_update_relationship(driver, target_node_uuid=character_uuid, relationship_type="MEMBER", properties=properties, direction=False)

    # Method to occupy a location
    def occupy_location(self, driver, location_uuid, properties=None):
        self.create_or_update_relationship(driver, target_node_uuid=location_uuid, relationship_type="OCCUPANT", properties=properties, direction=False)

    # Method to interact with another faction
    def interact_with(self, driver, other_faction_uuid, relationship_type="INTERACTS_WITH", properties=None, direction=True):
        self.create_or_update_relationship(driver, target_node_uuid=other_faction_uuid, relationship_type=relationship_type, properties=properties, direction=direction)

    # Method to retrieve all members of the faction
    def get_members(self, driver):
        return self.find_relationships(driver, relationship_type="MEMBER", unique_nodes=True, direction=False)

    # Method to retrieve all locations occupied by the faction
    def get_locations(self, driver):
        return self.find_relationships(driver, relationship_type="OCCUPANT", unique_nodes=True, direction=False)

    # Method to retrieve all factions this faction interacts with
    def get_interactions(self, driver, interaction_type=None):
        return self.find_relationships(driver, relationship_type=interaction_type or "INTERACTS_WITH", unique_nodes=True)
    
