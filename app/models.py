from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from flask_login import UserMixin

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class WorldObject(db.Model):
    __tablename__ = 'world_objects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False)  # Type of object (e.g., Character, Location, etc.)

    # Foreign key to the User model
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='world_objects')

    __mapper_args__ = {
        'polymorphic_identity': 'world_object',
        'polymorphic_on': type
    }

    def __repr__(self):
        return f'<{self.type} {self.name}>'

class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)  # Description of the skill

    # Foreign key to the User model
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='skills')

    def __repr__(self):
        return f'<Skill {self.name}>'

#Linkage relationships set ups
character_skills = db.Table('character_skills',
    db.Column('character_id', db.Integer, db.ForeignKey('characters.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skills.id'), primary_key=True),
    db.Column('value', db.Integer, nullable=False)  # The value of the skill for this specific character
)

character_inanimate = db.Table('character_inanimate',
    db.Column('character_id', db.Integer, db.ForeignKey('characters.id'), primary_key=True),
    db.Column('inanimate_id', db.Integer, db.ForeignKey('inanimates.id'), primary_key=True)
)

clan_relationships = db.Table('clan_relationships',
    db.Column('clan_id', db.Integer, db.ForeignKey('clans.id'), primary_key=True),
    db.Column('related_clan_id', db.Integer, db.ForeignKey('clans.id'), primary_key=True),
    db.Column('relationship_type', db.String(50), nullable=False)  # e.g., "ally", "at war"
)

class Character(WorldObject):
    __tablename__ = 'characters'
    id = db.Column(db.Integer, db.ForeignKey('world_objects.id'), primary_key=True)
    # Add character-specific attributes, e.g., health, skills, etc.

    # Relationship to the Skill model through the association table
    skills = db.relationship('Skill', secondary=character_skills, lazy='subquery',
                             backref=db.backref('characters', lazy=True))

    # Foreign key to the Clan/Faction model
    clan_id = db.Column(db.Integer, db.ForeignKey('clans.id'), nullable=True)
    clan = db.relationship('Clan', backref='members', foreign_keys=[clan_id])

    # Other relationships
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    location = db.relationship('Location', backref='residents', foreign_keys=[location_id])

    inanimates = db.relationship('Inanimate', secondary='character_inanimate', lazy='subquery',
                                 backref=db.backref('owners', lazy=True))

    __mapper_args__ = {
        'polymorphic_identity': 'character',
    }

    def __repr__(self):
        return f'<Character {self.name}>'


class Location(WorldObject):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, db.ForeignKey('world_objects.id'), primary_key=True)
    # Add location-specific attributes, e.g., coordinates, climate, etc.
    climate = db.Column(db.Text, nullable=True)

    __mapper_args__ = {
        'polymorphic_identity': 'location',
    }

    def __repr__(self):
        return f'<Location {self.name}>'
    

class Clan(WorldObject):
    __tablename__ = 'clans'
    id = db.Column(db.Integer, db.ForeignKey('world_objects.id'), primary_key=True)
    # Add clan-specific attributes, e.g., members, territory, etc.

    # Self-referential many-to-many relationship for clans
    related_clans = db.relationship(
        'Clan', secondary=clan_relationships,
        primaryjoin=id==clan_relationships.c.clan_id,
        secondaryjoin=id==clan_relationships.c.related_clan_id,
        backref='related_to', lazy='dynamic'
    )

    __mapper_args__ = {
        'polymorphic_identity': 'clan',
    }

    def __repr__(self):
        return f'<Clan {self.name}>'
    
class Inanimate(WorldObject):
    __tablename__ = 'inanimates'
    id = db.Column(db.Integer, db.ForeignKey('world_objects.id'), primary_key=True)
    # Add inanimate-specific attributes, e.g., material, usage, power, etc.

    __mapper_args__ = {
        'polymorphic_identity': 'inanimate',
    }

    def __repr__(self):
        return f'<Inanimate {self.name}>'


