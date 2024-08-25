
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask import session as flask_session
from flask_login import login_user, logout_user, login_required, current_user
from app import app, driver
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Hash the password
        hashed_password = generate_password_hash(password)

        with driver.session() as session:
            # Check if user already exists
            result = session.run("MATCH (u:User {username: $username}) RETURN u", username=username)
            if result.single():
                flash('Username already exists. Please try another one.')
                return redirect(url_for('signup'))

            # Create new user
            result = session.run(
                "CREATE (u:User {username: $username, email: $email, password_hash: $password_hash}) RETURN u",
                username=username, email=email, password_hash=hashed_password
            )
            user_node = result.single()["u"]
            new_user = User.from_node(user_node)

        # Log the user in
        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with driver.session() as session:
            result = session.run("MATCH (u:User {username: $username}) RETURN u", username=username)
            user_data = result.single()
            if user_data:
                user_node = user_data["u"]
                if check_password_hash(user_node["password_hash"], password):
                    user = User.from_node(user_node)
                    login_user(user)
                    return redirect(url_for('dashboard'))

        flash('Login failed. Check your username and password.')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    with driver.session() as session:
        result = session.run(
            """
            MATCH (u:User {username: $username})-[:OWNS]->(w:World)
            RETURN w
            """,
            username=current_user.username
        )
        worlds = [{"name": record["w"]["name"], "description": record["w"]["description"], "uuid": record["w"]["uuid"]} for record in result]

    return render_template('dashboard.html', worlds=worlds)

@app.route('/create_world', methods=['GET', 'POST'])
@login_required
def create_world():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        initial_timeline = request.form['initial_timeline']
        world_uuid = str(uuid.uuid4())  # Generate a unique identifier for the world

        with driver.session() as session:
            # Create the world node
            result = session.run(
                """
                MATCH (u:User {username: $username})
                CREATE (w:World {name: $name, description: $description, uuid: $uuid})
                CREATE (u)-[:OWNS]->(w)
                RETURN w
                """,
                username=current_user.username,
                name=name,
                description=description,
                uuid=world_uuid
            )
            world = result.single()["w"]

            timeline_uuid = str(uuid.uuid4())  # Generate a unique identifier for the timeline
            # Create the initial timeline for the world
            session.run(
                """
                MATCH (w:World {uuid: $uuid})
                CREATE (t:WorldTimeline {name: $timeline_name, uuid: $timeline_uuid})
                CREATE (w)-[:HAS_TIMELINE]->(t)
                """,
                uuid=world_uuid,
                timeline_name=initial_timeline,
                timeline_uuid=timeline_uuid
            )

        flash(f"World '{world['name']}' created successfully with initial timeline '{initial_timeline}'!")
        return redirect(url_for('dashboard'))

    return render_template('create_world.html')

@app.route('/enter_world/<world_uuid>', methods=['GET', 'POST'])
@login_required
def enter_world(world_uuid):
    flask_session['selected_world'] = world_uuid

    selected_timeline_name = None
    selected_timeline_uuid = flask_session.get('selected_timeline')
    world_nodes_by_type = {}

    with driver.session() as neo4j_session:
        result = neo4j_session.run(
            "MATCH (w:World {uuid: $world_uuid})-[:HAS_TIMELINE]->(t:WorldTimeline) RETURN w, collect(t) as timelines",
            world_uuid=world_uuid
        )
        record = result.single()
        world = record['w']
        timelines = record['timelines']

    if not selected_timeline_uuid and timelines:
        first_timeline = timelines[0]
        selected_timeline_uuid = first_timeline['uuid']
        selected_timeline_name = first_timeline['name']
        flask_session['selected_timeline'] = selected_timeline_uuid
    elif selected_timeline_uuid:
        with driver.session() as neo4j_session:
            result = neo4j_session.run(
                "MATCH (t:WorldTimeline {uuid: $timeline_uuid}) RETURN t.name AS name",
                timeline_uuid=selected_timeline_uuid
            )
            selected_timeline_name = result.single()["name"]

    if selected_timeline_uuid:
        with driver.session() as neo4j_session:
            result = neo4j_session.run(
                """
                MATCH (t:WorldTimeline {uuid: $timeline_uuid})-[:CONTAINS_NODE]->(n:WorldNode)
                RETURN n
                """,
                timeline_uuid=selected_timeline_uuid
            )
            nodes = [record["n"] for record in result]

            # Group nodes by their type
            for node in nodes:
                node_type = node.get('type')
                if node_type not in world_nodes_by_type:
                    world_nodes_by_type[node_type] = []
                world_nodes_by_type[node_type].append(node)

    return render_template(
        'world_dashboard.html',
        world=world,
        timelines=timelines,
        selected_timeline_name=selected_timeline_name,
        world_nodes_by_type=world_nodes_by_type,  # Pass the grouped nodes to the template
        selected_timeline_uuid=selected_timeline_uuid
    )

@app.route('/create_timeline/<uuid:world_uuid>', methods=['GET', 'POST'])
@login_required
def create_timeline(world_uuid):
    if request.method == 'POST':
        timeline_name = request.form['timeline_name']
        timeline_uuid = str(uuid.uuid4())  # Generate a unique identifier for the timeline

        with driver.session() as session:
            session.run(
                """
                MATCH (w:World {uuid: $world_uuid})
                CREATE (t:WorldTimeline {name: $timeline_name, uuid: $timeline_uuid})
                CREATE (w)-[:HAS_TIMELINE]->(t)
                """,
                world_uuid=str(world_uuid),
                timeline_name=timeline_name,
                timeline_uuid=timeline_uuid
            )
        
        flash(f"Timeline '{timeline_name}' created successfully!")
        return redirect(url_for('enter_world', world_uuid=world_uuid))

    return render_template('create_timeline.html')

@app.route('/create_node/<uuid:world_uuid>/<uuid:timeline_uuid>', methods=['GET', 'POST'])
@login_required
def create_node(world_uuid, timeline_uuid):
    if request.method == 'POST':
        node_name = request.form['node_name']
        node_type = request.form['node_type']
        node_description = request.form['node_description']
        node_uuid = str(uuid.uuid4())  # Generate a unique identifier for the node

        with driver.session() as session:
            session.run(
                """
                MATCH (w:World {uuid: $world_uuid})-[:HAS_TIMELINE]->(t:WorldTimeline {uuid: $timeline_uuid})
                CREATE (n:WorldNode {name: $node_name, type: $node_type, description: $node_description, uuid: $node_uuid})
                CREATE (t)-[:CONTAINS_NODE]->(n)
                """,
                world_uuid=str(world_uuid),
                timeline_uuid=str(timeline_uuid),
                node_name=node_name,
                node_type=node_type,
                node_description=node_description,
                node_uuid=node_uuid
            )
        
        flash(f"World Node '{node_name}' created successfully!")
        return redirect(url_for('enter_world', world_uuid=world_uuid))

    return render_template('create_node.html', world_uuid=world_uuid, timeline_uuid=timeline_uuid)


@app.route('/edit_node/<uuid:world_uuid>/<uuid:node_uuid>', methods=['GET', 'POST'])
@login_required
def edit_node(world_uuid, node_uuid):
    world_uuid_str = str(world_uuid)
    node_uuid_str = str(node_uuid)
    selected_timeline_uuid_str = flask_session.get('selected_timeline')

    if request.method == 'POST':
        node_name = request.form.get('node_name')
        node_type = request.form.get('node_type')
        node_description = request.form.get('node_description')

        with driver.session() as session:
            session.run(
                """
                MATCH (n:WorldNode {uuid: $node_uuid})
                SET n.name = $node_name, n.type = $node_type, n.description = $node_description
                """,
                node_uuid=node_uuid_str,
                node_name=node_name,
                node_type=node_type,
                node_description=node_description
            )

        # Process relationships
        relationships = request.form.to_dict(flat=False)
        print(f"Relationships submitted: {relationships}")  # Debugging output

        for i in range(len(relationships.get('relationships[0][target_node_uuid]', []))):
            target_node_uuid = relationships[f'relationships[{i}][target_node_uuid]'][0]
            relationship_type = relationships[f'relationships[{i}][type]'][0]
            relationship_params = relationships[f'relationships[{i}][params]'][0]

            if target_node_uuid and relationship_type:
                try:
                    with driver.session() as session:
                        # Dynamically construct the Cypher query with the relationship type
                        query = f"""
                            MATCH (n1:WorldNode {{uuid: $node_uuid}}), (n2:WorldNode {{uuid: $target_node_uuid}})
                            MERGE (n1)-[r:{relationship_type}]->(n2)
                        """
                        # If there are any parameters, add them
                        if relationship_params:
                            query += " SET r += $relationship_params"

                        session.run(
                            query,
                            node_uuid=node_uuid_str,
                            target_node_uuid=str(target_node_uuid),
                            relationship_params=relationship_params
                        )
                    print("Relationship created/updated successfully.")  # Debugging output
                except Exception as e:
                    print(f"Error creating/updating relationship: {e}")  # Debugging output

        flash('Node and relationships updated successfully!')
        return redirect(url_for('enter_world', world_uuid=world_uuid_str))

    # On GET request, fetch node details and existing relationships
    with driver.session() as session:
        node_result = session.run(
            "MATCH (n:WorldNode {uuid: $node_uuid}) RETURN n",
            node_uuid=node_uuid_str
        )
        node = node_result.single()['n']

        relationships_result = session.run(
            "MATCH (n:WorldNode {uuid: $node_uuid})-[r]->(m) RETURN r, m",
            node_uuid=node_uuid_str
        )
        relationships = [
            {"relationship": record["r"], "target_node": record["m"]}
            for record in relationships_result
        ]

        # Fetch all nodes in the selected timeline except the current node
        all_nodes_result = session.run(
            """
            MATCH (t:WorldTimeline {uuid: $timeline_uuid})-[:CONTAINS_NODE]->(n:WorldNode)
            WHERE n.uuid <> $node_uuid
            RETURN n
            """,
            timeline_uuid=selected_timeline_uuid_str,
            node_uuid=node_uuid_str
        )
        all_nodes = [record["n"] for record in all_nodes_result]

    return render_template(
        'edit_node.html',
        node=node,
        relationships=relationships,
        all_nodes=all_nodes,
        world_uuid=world_uuid_str
    )