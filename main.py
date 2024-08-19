from app import app, driver

def wipe_neo4j_database():
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

if __name__ == '__main__':
    wipe_neo4j_database()  # Wipe the database before starting the app
    app.run(debug=True, port=5001)