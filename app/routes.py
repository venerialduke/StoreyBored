from openai import OpenAI
import os
from flask import render_template, flash, redirect, url_for, request
from app import app, db, login
from app.models import Character, Location, Clan, Inanimate, Skill, WorldObject, character_skills, character_inanimate, User, clan_relationships
#from werkzeug.urls import url_parse
from flask_login import current_user, login_user, logout_user, login_required, LoginManager

# Set your OpenAI API key
client = OpenAI(
  api_key=os.environ['OPENAI_API_KEY'],  # this is also the default, it can be omitted
)

print(f"API Key: {os.environ['OPENAI_API_KEY']}")

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    characters = Character.query.filter_by(user_id=current_user.id).all()
    skills = Skill.query.filter_by(user_id=current_user.id).all()
    locations = Location.query.filter_by(user_id=current_user.id).all()
    inanimates = Inanimate.query.filter_by(user_id=current_user.id).all()
    clans = Clan.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', characters=characters,skills=skills,locations=locations,inanimates=inanimates,clans=clans)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create_world_component', methods=['GET'])
@login_required
def create_world_component():
    return render_template('create_world_component.html')

@app.route('/save_world_component', methods=['POST'])
@login_required
def save_world_component():
    component_type = request.form['component-type']
    name = request.form['name']
    description = request.form.get('description', '')

    if component_type == 'Character':
        character = Character.query.filter_by(name=name, user_id=current_user.id).first()
        if not character:
            character = Character(name=name, description=description, user_id=current_user.id)
            db.session.add(character)

        # Handle related skills with values
        skills = request.form.getlist('skills[]')
        skill_values = request.form.getlist('skill-values[]')
        for skill_name, skill_value in zip(skills, skill_values):
            skill = Skill.query.filter_by(name=skill_name, user_id=current_user.id).first()
            if not skill:
                skill = Skill(name=skill_name, user_id=current_user.id)
                db.session.add(skill)
            # Insert into the character_skills association table
            stmt = character_skills.insert().values(character_id=character.id, skill_id=skill.id, value=int(skill_value))
            db.session.execute(stmt)

        # Handle related inanimates
        inanimates = request.form.getlist('inanimates[]')
        for inanimate_name in inanimates:
            inanimate = Inanimate.query.filter_by(name=inanimate_name, user_id=current_user.id).first()
            if not inanimate:
                inanimate = Inanimate(name=inanimate_name, user_id=current_user.id)
                db.session.add(inanimate)
            character.inanimates.append(inanimate)

        # Handle location
        location_name = request.form.get('location-input', '').strip()
        if location_name:
            location = Location.query.filter_by(name=location_name, user_id=current_user.id).first()
            if not location:
                location = Location(name=location_name, user_id=current_user.id)
                db.session.add(location)
            character.location = location

        # Handle clan
        clan_name = request.form.get('clan-input', '').strip()
        if clan_name:
            clan = Clan.query.filter_by(name=clan_name, user_id=current_user.id).first()
            if not clan:
                clan = Clan(name=clan_name, user_id=current_user.id)
                db.session.add(clan)
            character.clan = clan

        db.session.commit()

    elif component_type == 'Location':
        location = Location.query.filter_by(name=name, user_id=current_user.id).first()
        if not location:
            location = Location(name=name, description=description, user_id=current_user.id)
            db.session.add(location)

        climate = request.form.get('climate', '')
        if climate:
            location.climate = climate

        db.session.commit()

    elif component_type == 'Clan':
        clan = Clan.query.filter_by(name=name, user_id=current_user.id).first()
        if not clan:
            clan = Clan(name=name, description=description, user_id=current_user.id)
            db.session.add(clan)
            db.session.commit()  # Commit to get the ID for the new clan

        # Handle related clans with relationship types
        related_clans = request.form.getlist('related-clans[]')
        relationship_types = request.form.getlist('relationship-types[]')
        for related_clan_name, relationship_type in zip(related_clans, relationship_types):
            related_clan = Clan.query.filter_by(name=related_clan_name, user_id=current_user.id).first()
            if not related_clan:
                related_clan = Clan(name=related_clan_name, user_id=current_user.id)
                db.session.add(related_clan)
                db.session.commit()  # Commit to get the ID for the new related clan
            
            # Now that we have the ID, insert into the association table
            stmt = clan_relationships.insert().values(clan_id=clan.id, related_clan_id=related_clan.id, relationship_type=relationship_type)
            db.session.execute(stmt)

        db.session.commit()

    elif component_type == 'Inanimate':
        inanimate = Inanimate.query.filter_by(name=name, user_id=current_user.id).first()
        if not inanimate:
            inanimate = Inanimate(name=name, description=description, user_id=current_user.id)
            db.session.add(inanimate)
        db.session.commit()

    elif component_type == 'Skill':
        skill = Skill.query.filter_by(name=name, user_id=current_user.id).first()
        if not skill:
            skill = Skill(name=name, description=description, user_id=current_user.id)
            db.session.add(skill)
        db.session.commit()

    return redirect(url_for('dashboard'))

@app.route('/edit_world_component/<component_type>/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_world_component(component_type, id):
    # Retrieve the component based on the type and ID
    if component_type == 'Character':
        component = Character.query.get_or_404(id)

        # Prepare a list of skills with their associated values for this character
        skills_with_values = []
        for skill in component.skills:
            value = db.session.query(character_skills.c.value).filter_by(character_id=component.id, skill_id=skill.id).scalar()
            skills_with_values.append((skill, value))

        related_clans = []

    elif component_type == 'Location':
        component = Location.query.get_or_404(id)
        skills_with_values = []  # No skills for locations, but we need to pass this to the template
        related_clans = []

    elif component_type == 'Inanimate':
        component = Inanimate.query.get_or_404(id)
        skills_with_values = []  # No skills for locations, but we need to pass this to the template
        related_clans = []

    elif component_type == 'Clan':
        component = Clan.query.get_or_404(id)
        
        # Fetch related clans and their relationship types
        related_clans = []
        relationships = db.session.query(clan_relationships).filter_by(clan_id=component.id).all()
        for relationship in relationships:
            related_clan = Clan.query.get(relationship.related_clan_id)
            related_clans.append((related_clan, relationship.relationship_type))

        skills_with_values = []  # No skills for clans, but we need to pass this to the template


    else:
        flash("Invalid component type.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Update component with form data
        component.name = request.form['name']
        component.description = request.form.get('description', component.description)

        if component_type == 'Character':
            # Handle skills update
            component.skills = []  # Clear existing skills
            skills = request.form.getlist('skills[]')
            skill_values = request.form.getlist('skill-values[]')
            
            for skill_name, skill_value in zip(skills, skill_values):
                # Find or create the skill
                skill = Skill.query.filter_by(name=skill_name, user_id=current_user.id).first()
                if not skill:
                    skill = Skill(name=skill_name, user_id=current_user.id)
                    db.session.add(skill)
                
                # Add the skill to the character with the specific value
                stmt = character_skills.insert().values(character_id=component.id, skill_id=skill.id, value=int(skill_value))
                db.session.execute(stmt)

            # Handle location update
            location_name = request.form.get('location-input', '').strip()
            if location_name:
                location = Location.query.filter_by(name=location_name, user_id=current_user.id).first()
                if not location:
                    location = Location(name=location_name, user_id=current_user.id)
                    db.session.add(location)
                component.location = location

            # Handle clan update
            clan_name = request.form.get('clan-input', '').strip()
            if clan_name:
                clan = Clan.query.filter_by(name=clan_name, user_id=current_user.id).first()
                if not clan:
                    clan = Clan(name=clan_name, user_id=current_user.id)
                    db.session.add(clan)
                component.clan = clan

            # Handle inanimate update
            component.inanimates = []  # Clear existing inanimates
            inanimates = request.form.getlist('inanimates[]')
            for inanimate_name in inanimates:
                inanimate = Inanimate.query.filter_by(name=inanimate_name, user_id=current_user.id).first()
                if not inanimate:
                    inanimate = Inanimate(name=inanimate_name, user_id=current_user.id)
                    db.session.add(inanimate)
                component.inanimates.append(inanimate)

        elif component_type == 'Location':
            # Handle climate update
            component.climate = request.form.get('climate', component.climate)

        elif component_type == 'Clan':
            # Update clan relationships
            db.session.query(clan_relationships).filter_by(clan_id=component.id).delete()  # Clear existing relationships

            related_clans = request.form.getlist('related-clans[]')
            relationship_types = request.form.getlist('relationship-types[]')
            for related_clan_name, relationship_type in zip(related_clans, relationship_types):
                related_clan = Clan.query.filter_by(name=related_clan_name, user_id=current_user.id).first()
                if not related_clan:
                    related_clan = Clan(name=related_clan_name, user_id=current_user.id)
                    db.session.add(related_clan)
                    db.session.commit()  # Commit to get the ID for the new related clan
                
                # Now that we have the ID, insert into the association table
                stmt = clan_relationships.insert().values(clan_id=component.id, related_clan_id=related_clan.id, relationship_type=relationship_type)
                db.session.execute(stmt)

        db.session.commit()
        flash(f"{component_type} updated successfully!")
        return redirect(url_for('dashboard'))

    # Render the edit template with the current component data
    return render_template('edit_world_component.html', component=component, component_type=component_type, skills_with_values=skills_with_values,related_clans=related_clans)

@app.route('/generate_story')
@login_required
def generate_story():
    # Gather all characters for the current user
    characters = Character.query.filter_by(user_id=current_user.id).all()

    # Create a context string with all character names and descriptions
    context = "The following characters are involved in this story:\n"
    for character in characters:
        context += f"Name: {character.name}, Description: {character.description}\n"

    # Generate the story using the correct OpenAI method
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use "gpt-4" if you're using GPT-4
        messages=[
            {"role": "system", "content": "You are a creative story writer."},
            {"role": "user", "content": f"{context} Write a short story involving these characters."}
        ]
    )

    #story = response['choices'][0]['message']['content'].strip()
    story = response.choices[0].message.content

    return render_template('story.html', story=story)