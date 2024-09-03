from flask import Blueprint, render_template, request, redirect, url_for, session, flash
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
        nodes = world.get_nodes(driver)
        
        # Convert nodes and relationships into the format required by the frontend
        graph_data = []
        for node in nodes:
            graph_data.append({
                'id': node['properties']['uuid'],  # Extract 'uuid' from node's properties
                'label': node['labels'][0],  # Assuming the first label is the main one
                'name': node['properties']['name']
            })

        return render_template('edit_world.html', world=world, graph_data=graph_data)

    return app_routes