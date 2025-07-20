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
    pref_gender   = Column(String, default="")  # NUEVO: preferencia de género
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

engine = create_engine(config.DB_URL, echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

class Database:
    def __init__(self, db_url):
        self.engine = create_engine(db_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)

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

    def has_profile(self, user_id):
        s = self.Session()
        u = s.get(User, user_id)
        res = bool(u and u.photo_file_id)
        s.close()
        return res

    def save_profile(self, user_id, photo_file_id, description, instagram, gender, pref_gender, country, city):
        s = self.Session()
        u = s.get(User, user_id)
        if u:
            u.photo_file_id = photo_file_id
            u.description   = description
            u.instagram     = instagram
            u.gender        = gender
            u.pref_gender   = pref_gender
            u.country       = country
            u.city          = city
            s.commit()
        s.close()

    def get_profile(self, user_id):
        s = self.Session()
        u = s.get(User, user_id)
        s.close()
        return u

    def delete_profile(self, user_id):
        s = self.Session()
        u = s.get(User, user_id)
        if u:
            u.photo_file_id = ""
            u.description   = ""
            u.instagram     = ""
            u.gender        = ""
            u.pref_gender   = ""
            u.country       = ""
            u.city          = ""
            s.commit()
        s.close()

    def get_potential_matches(self, user_id):
        s = self.Session()
        me = s.get(User, user_id)
        # filtro por preferencia mutua y ubicación
        users = s.query(User).filter(
            User.id != user_id,
            User.photo_file_id != "",
            User.gender == me.pref_gender,
            me.gender == User.pref_gender,
            User.country == me.country,
            User.city == me.city,
        ).all()
        s.close()
        return users

    def record_like(self, user_id, target_id):
        s = self.Session()
        exists = s.query(Like).filter_by(user_id=user_id, target_id=target_id).first()
        if not exists:
            s.add(Like(user_id=user_id, target_id=target_id))
            s.commit()
        mutual = s.query(Like).filter_by(user_id=target_id, target_id=user_id).first()
        s.close()
        return bool(mutual)

    def get_all_user_ids(self):
        s = self.Session()
        ids = [u.id for u in s.query(User).all()]
        s.close()
        return ids
