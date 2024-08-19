from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

    @classmethod
    def from_node(cls, node):
        return cls(
            id=node.id,
            username=node.get('username'),
            email=node.get('email'),
            password_hash=node.get('password_hash')
        )

    def get_id(self):
        return str(self.id)  # Neo4j node IDs might not be integers