from sqlalchemy.orm import sessionmaker

from ..database import engine, Base
from ..models import Role

def initialize_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed roles
    roles_to_create = ['admin', 'master', 'dealer', 'player']
    for role_name in roles_to_create:
        if not session.query(Role).filter_by(name=role_name).first():
            session.add(Role(name=role_name))
    
    session.commit()
    print("Roles seeded successfully.")
    session.close()

if __name__ == "__main__":
    initialize_database()