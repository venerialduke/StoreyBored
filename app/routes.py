from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.utils import User, World, NODE
import os

def create_app_routes(driver):
    app_routes = Blueprint('app_routes', __name__, template_folder='templates')

    @app_routes.route('/')
    def home():
        return render_template('login.html')

    @app_routes.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            user = User(username=username)
            if user.verify_password(driver, password):
                session['user_id'] = user.uuid
                flash(f'Welcome back, {username}!', 'success')
                return redirect(url_for('app_routes.dashboard'))
            else:
                flash('Invalid username or password', 'danger')

        return render_template('login.html')

    @app_routes.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            print("Register form submitted")

            username = request.form['username']
            password = request.form['password']
            email = request.form['email']

            print(f"Username: {username}, Email: {email}")

            user = User(username=username, properties={'email': email})
            if user.register(driver, password):
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('app_routes.login'))
            else:
                flash('Username already exists. Please choose another one.', 'danger')

        return render_template('register.html')

    @app_routes.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('app_routes.login'))

        user = User.from_database(driver, session['user_id'])
        worlds = user.get_worlds(driver)

        return render_template('dashboard.html', worlds=worlds)

    @app_routes.route('/logout')
    def logout():
        session.pop('user_id', None)
        flash('You have been logged out.', 'info')
        return redirect(url_for('app_routes.login'))
    
    @app_routes.route('/create_world', methods=['GET', 'POST'])
    def create_world():
        if 'user_id' not in session:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('app_routes.login'))

        user = User.from_database(driver, session['user_id'])

        if request.method == 'POST':
            world_name = request.form['world_name']
            world_properties = {
                'description': request.form.get('description', ''),
                'pop_limit': request.form.get('pop_limit', 0)
            }
            user.create_world(driver, world_name=world_name, world_properties=world_properties)
            flash(f'World {world_name} created successfully!', 'success')
            return redirect(url_for('app_routes.dashboard'))

        return render_template('create_world.html')
    
    @app_routes.route('/enter_world/<world_uuid>', methods=['GET'])
    def enter_world(world_uuid):
        if 'user_id' not in session:
            flash('You need to log in first.', 'warning')
            return redirect(url_for('app_routes.login'))

        world = World.from_database(driver, uuid=world_uuid)
        nodes = world.get_nodes(driver)

        return render_template('world_dashboard.html', world=world, nodes=nodes)
    
    @app_routes.route('/world/<world_uuid>/create_node', methods=['GET', 'POST'])
    def create_node(world_uuid):
        world = World.from_database(driver, uuid=world_uuid)

        if request.method == 'POST':
            # Get the node type (label) and name
            label = request.form.get('node_type')
            name = request.form.get('node_name')
            
            # Handle custom type input
            if label == 'custom':
                label = request.form.get('custom_type')

            # Basic properties
            node_properties = {'name': name}
            
            # Collect additional properties from the form
            property_names = request.form.getlist('property_name[]')
            property_values = request.form.getlist('property_value[]')
            
            # Add each additional property to the node properties
            for prop_name, prop_value in zip(property_names, property_values):
                if prop_name and prop_value:
                    node_properties[prop_name] = prop_value

            # Create or update the node
            world.create_or_update_node(driver, node_label=label, node_properties=node_properties)
            flash(f'{label} "{name}" has been created.', 'success')
            return redirect(url_for('app_routes.enter_world', world_uuid=world_uuid))

        return render_template('create_node.html', world=world)
    
    @app_routes.route('/world/<world_uuid>/delete_node/<node_uuid>', methods=['POST'])
    def delete_node(world_uuid, node_uuid):
        world = World.from_database(driver, uuid=world_uuid)
        node = NODE.from_database(driver, uuid=node_uuid)
        
        # First, delete all relationships related to the node
        with driver.session() as session:
            session.run("MATCH (n {uuid: $uuid})-[r]-() DELETE r", uuid=node_uuid)
        
        # Then, delete the node itself
        with driver.session() as session:
            session.run("MATCH (n {uuid: $uuid}) DELETE n", uuid=node_uuid)

        flash(f'Node {node.properties["name"]} has been deleted.', 'success')
        return redirect(url_for('app_routes.enter_world', world_uuid=world_uuid))


    @app_routes.route('/world/<world_uuid>/edit', methods=['GET'])
    def edit_world(world_uuid):
        world = World.from_database(driver, uuid=world_uuid)
        nodes = world.get_nodes(driver)  # Fetching nodes

        graph_data = {
            'nodes': [],
            'edges': []
        }

        # Populate nodes
        for node in nodes:
            node_properties = node.get('properties', {})
            node_id = node_properties.get('uuid', 'undefined_uuid')
            node_name = node_properties.get('name', 'Unnamed Node')
            node_labels = node.get('labels', ['Unknown'])

            if node_id != 'undefined_uuid':
                graph_data['nodes'].append({
                    'id': node_id,
                    'label': node_name,
                    'group': node_labels[0] if node_labels else 'Unknown'
                })

        # Retrieve relationships (edges)
        with driver.session() as session:
            result = session.run("""
                MATCH (n)-[r]->(m)
                WHERE n.uuid IN $node_ids AND m.uuid IN $node_ids
                RETURN n.uuid AS from, m.uuid AS to, TYPE(r) AS rel_type
            """, node_ids=[node['properties']['uuid'] for node in nodes])

            for record in result:
                graph_data['edges'].append({
                    'from': record['from'],
                    'to': record['to'],
                    'label': record['rel_type']
                })

        # Debugging: Print to verify if data is correct
        print(f"Graph Data Nodes: {graph_data['nodes']}")
        print(f"Graph Data Edges: {graph_data['edges']}")

        return render_template('edit_world.html', world=world, graph_data=graph_data)

    @app_routes.route('/world/<world_uuid>/update_node', methods=['POST'])
    def update_node(world_uuid):
        data = request.get_json()

        print("Data received:", data)  # Debug print

        if 'node_id' not in data:
            return jsonify({'error': 'Missing node_id'}), 400

        try:
            node = NODE.from_database(driver, uuid=data['node_id'])
            print(f"Node found: {node}")

            # Update node properties
            node.properties['name'] = data['node_name']
            node.properties.update(data['node_properties'])
            print("Updated properties:", node.properties)

            # Save the changes to the database
            node.create_or_update(driver)
            print("Node updated successfully")

            return jsonify({'status': 'success'}), 200
        except Exception as e:
            print(f"Error updating node: {e}")
            return jsonify({'error': str(e)}), 500

    @app_routes.route('/world/<world_uuid>/create_relationship', methods=['POST'])
    def create_relationship(world_uuid):
        data = request.get_json()

        node1 = NODE.from_database(driver, uuid=data['node1'])
        node2 = NODE.from_database(driver, uuid=data['node2'])

        # Create relationship
        node1.create_or_update_relationship(driver, target_node_uuid=node2.uuid,
                                            relationship_type=data['rel_type'],
                                            properties=data['rel_properties'],
                                            direction=False)
        return jsonify({'status': 'success'}), 200

    return app_routes


