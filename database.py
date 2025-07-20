# database.py

import config
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    fullname      = Column(String)
    is_premium    = Column(Boolean, default=False)
    photo_file_id = Column(String, default="")
    description   = Column(String, default="")
    instagram     = Column(String, default="")
    gender        = Column(String, default="")
    country       = Column(String, default="")
    city          = Column(String, default="")

    likes_sent     = relationship(
        "Like", back_populates="sender",
        foreign_keys="Like.user_id",
        cascade="all, delete-orphan"
    )
    likes_received = relationship(
        "Like", back_populates="target",
        foreign_keys="Like.target_id",
        cascade="all, delete-orphan"
    )

class Like(Base):
    __tablename__ = "likes"
    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, ForeignKey("users.id"))
    target_id = Column(Integer, ForeignKey("users.id"))

    sender = relationship("User", foreign_keys=[user_id], back_populates="likes_sent")
    target = relationship("User", foreign_keys=[target_id], back_populates="likes_received")

# Create engine and tables if they don't yet exist
engine = create_engine(config.DB_URL, echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

class Database:
    def __init__(self, db_url):
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)

    # User registration
    def register_user(self, user_id, fullname):
        session = self.Session()
        if not session.get(User, user_id):
            session.add(User(id=user_id, fullname=fullname))
            session.commit()
        session.close()

    def unregister_user(self, user_id):
        session = self.Session()
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()
        session.close()

    # Premium status
    def set_premium(self, user_id):
        session = self.Session()
        user = session.get(User, user_id)
        if user and not user.is_premium:
            user.is_premium = True
            session.commit()
        session.close()

    def is_premium(self, user_id):
        session = self.Session()
        user = session.get(User, user_id)
        result = bool(user and user.is_premium)
        session.close()
        return result

    # Profile methods
    def has_profile(self, user_id):
        session = self.Session()
        user = session.get(User, user_id)
        result = bool(user and user.photo_file_id)
        session.close()
        return result

    def save_profile(self, user_id, photo_file_id, description, instagram, gender, country, city):
        session = self.Session()
        user = session.get(User, user_id)
        if user:
            user.photo_file_id = photo_file_id
            user.description   = description
            user.instagram     = instagram
            user.gender        = gender
            user.country       = country
            user.city          = city
            session.commit()
        session.close()

    def get_profile(self, user_id):
        session = self.Session()
        user = session.get(User, user_id)
        session.close()
        return user

    def delete_profile(self, user_id):
        session = self.Session()
        user = session.get(User, user_id)
        if user:
            user.photo_file_id = ""
            user.description   = ""
            user.instagram     = ""
            user.gender        = ""
            user.country       = ""
            user.city          = ""
            session.commit()
        session.close()

    # Matching and likes
    def get_potential_matches(self, user_id):
        session = self.Session()
        users = session.query(User).filter(
            User.id != user_id,
            User.photo_file_id != ""
        ).all()
        session.close()
        return users

    def record_like(self, user_id, target_id):
        session = self.Session()
        # Avoid duplicates
        existing = session.query(Like).filter_by(user_id=user_id, target_id=target_id).first()
        if not existing:
            session.add(Like(user_id=user_id, target_id=target_id))
            session.commit()
        # Check mutual like
        mutual = session.query(Like).filter_by(user_id=target_id, target_id=user_id).first()
        session.close()
        return bool(mutual)

    # Utility
    def get_all_user_ids(self):
        session = self.Session()
        ids = [u.id for u in session.query(User).all()]
        session.close()
        return ids
