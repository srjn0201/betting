from sqlalchemy.orm import sessionmaker

from ..database import engine, Base
from ..models import Role, User, Transaction
from .. import security

def seed_roles(session):
    """Seeds the database with default user roles."""
    print("Seeding roles...")
    roles_to_create = ['admin', 'master', 'dealer', 'player']
    
    for role_name in roles_to_create:
        if not session.query(Role).filter_by(name=role_name).first():
            session.add(Role(name=role_name))
    
    session.commit()
    print("Roles seeded successfully.")

def seed_initial_users(session):
    """Seeds the database with initial admin/master users if none exist."""
    user_count = session.query(User).count()
    if user_count > 0:
        print("Users table is not empty. Skipping initial user seeding.")
        return

    print("Users table is empty. Seeding initial admin and master users...")
    
    # 1. Create Admin User
    admin_role = session.query(Role).filter_by(name='admin').one()
    admin_user = User(
        username="admin",
        hashed_password=security.get_password_hash("adminpassword"),
        role_id=admin_role.id,
        parent_user_id=None  # Admin has no parent
    )
    session.add(admin_user)
    session.flush()  # Flush to assign an ID to admin_user before using it

    # 2. Create Master User
    master_role = session.query(Role).filter_by(name='master').one()
    master_user = User(
        username="master",
        hashed_password=security.get_password_hash("masterpassword"),
        role_id=master_role.id,
        parent_user_id=admin_user.id  # Master's parent is the admin
    )
    session.add(master_user)
    
    session.commit()
    print("Default admin and master users created.")

def initialize_database():
    """Main function to initialize the database."""
    print("--- Starting Database Initialization ---")
    
    # 1. Create all tables
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 2. Seed roles first
        seed_roles(session)
        
        # 3. Seed initial users after roles are created
        seed_initial_users(session)
    finally:
        session.close()
        print("--- Database Initialization Complete ---")

# if __name__ == "__main__":
#     initialize_database()       # 2. Seed roles first
#     seed_roles(session)
        
#         # 3. Seed initial users after roles are created
#     seed_initial_users(session)
#     finally:
#     session.close()
#     print("--- Database Initialization Complete ---")

if __name__ == "__main__":
    initialize_database()