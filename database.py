import config from sqlalchemy import create_engine, Column, Integer, String, Boolean from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base): tablename = "users" id = Column(Integer, primary_key=True) fullname = Column(String) is_premium = Column(Boolean, default=False)

engine = create_engine(config.DB_URL, echo=False) Session = sessionmaker(bind=engine) Base.metadata.create_all(engine)

class Database: def init(self, db_url): self.engine = create_engine(db_url, echo=False) self.Session = sessionmaker(bind=self.engine)

def register_user(self, user_id, fullname):
    s = self.Session()
    if not s.get(User, user_id):
        s.add(User(id=user_id, fullname=fullname))
        s.commit()
    s.close()

def unregister_user(self, user_id):
    s = self.Session()
    u = s.get(User, user_id)
    if u:
        s.delete(u)
        s.commit()
    s.close()

def set_premium(self, user_id):
    s = self.Session()
    u = s.get(User, user_id)
    if u and not u.is_premium:
        u.is_premium = True
        s.commit()
    s.close()

def is_premium(self, user_id):
    s = self.Session()
    u = s.get(User, user_id)
    res = bool(u and u.is_premium)
    s.close()
    return res

def get_matches(self, version=False):
    s = self.Session()
    if version:
        users = s.query(User).filter_by(is_premium=True).all()
    else:
        users = s.query(User).all()
    res = [f"{u.fullname} (ID: {u.id})" for u in users]
    s.close()
    return res

