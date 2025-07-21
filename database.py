# database.py
from sqlalchemy import (
    Column, Integer, String, Boolean, create_engine
)
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    fullname      = Column(String, nullable=False)
    is_premium    = Column(Boolean, default=False)
    photo_file_id = Column(String, nullable=True)
    description   = Column(String, nullable=True)
    instagram     = Column(String, nullable=True)
    gender        = Column(String, nullable=True)
    pref_gender   = Column(String, nullable=True)
    country       = Column(String, nullable=True)
    city          = Column(String, nullable=True)
    super_likes   = Column(Integer, default=0)

class Database:
    def __init__(self, url):
        self.engine = create_engine(url, echo=False, future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def register_user(self, user_id: int, fullname: str):
        with self.Session() as s:
            if not s.get(User, user_id):
                s.add(User(id=user_id, fullname=fullname))
                s.commit()

    def unregister_user(self, user_id: int):
        with self.Session() as s:
            u = s.get(User, user_id)
            if u:
                s.delete(u)
                s.commit()

    def has_profile(self, user_id: int) -> bool:
        with self.Session() as s:
            u = s.get(User, user_id)
            return bool(u and u.photo_file_id)

    def save_profile(self, user_id: int, **fields):
        with self.Session() as s:
            u = s.get(User, user_id)
            for k, v in fields.items():
                setattr(u, k, v)
            s.commit()

    def get_profile(self, user_id: int) -> User:
        with self.Session() as s:
            return s.get(User, user_id)

    def delete_profile(self, user_id: int):
        with self.Session() as s:
            u = s.get(User, user_id)
            if u:
                # reset profile fields
                u.photo_file_id = None
                u.description = None
                u.instagram = None
                u.gender = None
                u.pref_gender = None
                u.country = None
                u.city = None
                s.commit()

    def get_potential_matches(self, user_id: int):
        """Devuelve lista de usuarios con perfil, distinto a user_id."""
        with self.Session() as s:
            me = s.get(User, user_id)
            if not me: return []
            # filtro simple: misma ciudad y género preferido
            return s.query(User).filter(
                User.id != user_id,
                User.photo_file_id.isnot(None),
                User.gender == me.pref_gender,
                User.city == me.city
            ).all()

    def record_like(self, from_id: int, to_id: int):
        # opcional: guardar en tabla aparte
        pass

    def get_user(self, user_id: int) -> User:
        return self.get_profile(user_id)

    def purchase_super_likes(self, user_id: int, count: int):
        with self.Session() as s:
            u = s.get(User, user_id)
            u.super_likes = (u.super_likes or 0) + count
            s.commit()

    def use_super_like(self, user_id: int) -> bool:
        with self.Session() as s:
            u = s.get(User, user_id)
            if u and (u.super_likes or 0) > 0:
                u.super_likes -= 1
                s.commit()
                return True
            return False

    def is_premium(self, user_id: int) -> bool:
        with self.Session() as s:
            u = s.get(User, user_id)
            return bool(u and u.is_premium)
