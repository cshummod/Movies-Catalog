from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, User
from database_setup import engine


Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Seed database with categories
action = Category(name="Action")
session.add(action)
session.commit()

comedy = Category(name="Comedy")
session.add(comedy)
session.commit()

horror = Category(name="Horror")
session.add(horror)
session.commit()

sci_fi = Category(name="Science Fiction")
session.add(sci_fi)
session.commit()

adventure = Category(name="Adventure")
session.add(adventure)
session.commit()

drama = Category(name="Drama")
session.add(drama)
session.commit()


print("Database has been seeded successfully.")
