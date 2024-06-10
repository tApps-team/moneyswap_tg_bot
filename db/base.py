from sqlalchemy.ext.automap import automap_base
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

from config import db_url


Base = automap_base()

engine = create_engine(db_url,
                       echo=True)

# Base.prepare(engine, reflect=True)
Base.prepare(autoload_with=engine)

session = sessionmaker(engine, expire_on_commit=False)