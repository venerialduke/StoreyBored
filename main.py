from app import app, db
from config import Config  # Import the Config class

# Apply the configuration to the Flask app
app.config.from_object(Config)

# Automatically create the tables if they don't exist
with app.app_context():
    #db.drop_all()
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)