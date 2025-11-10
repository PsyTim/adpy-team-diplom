import sqlalchemy as sq
from sqlalchemy import DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()



class Users(Base):
    __tablename__ = "users" # имя таблицы
# создаем колонки:
    id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True)
    gender = sq.Column(sq.Integer, unique=False)
    birthday = sq.Column(sq.String(length=20), unique=False)
    city_id = sq.Column(sq.Integer, unique=False)
    city = sq.Column(sq.String(length=100), unique=False)
    last_visit = sq.Column(DateTime)
    filter_age_from = sq.Column(sq.Integer, unique=False)
    filter_age_to = sq.Column(sq.Integer, unique=False)
    filter_gender = sq.Column(sq.String(length=1), unique=False)
# метод для вывода данных из таблицы в виде строки через пробел
#     def __str__(self):
#         return f'{self.word_id} {self.word} {self.translate}'


class Profiles(Base):
    __tablename__ = "profiles" # имя таблицы
# создаем колонки:
    id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True)
    city = sq.Column(sq.String(length=100), unique=False)
    birthday = sq.Column(sq.String(length=20), unique=False)
    favorites_id = sq.Column(sq.Integer, sq.ForeignKey("favorites.id"))

class UserProfiles(Base):
    __tablename__ = "user_profiles"

    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey("users.id"), nullable=False)
    profile_id = sq.Column(sq.Integer, sq.ForeignKey("profiles.id"), nullable=False)

    profiles = relationship(Profiles, backref="profiles_ref")
    users = relationship(Users, backref="users_ref")

class Favorites(Base):
    __tablename__ = "favorites"

    id = sq.Column(sq.Integer, primary_key=True)
    profile_id = sq.Column(sq.Integer, nullable=False)
    favorite_id = sq.Column(sq.Integer, unique=True)
    favorite_info = sq.Column(sq.String(length=200), unique=True)

    profiles2 = relationship(Profiles, backref="profiles_ref2")


# функция для создания таблиц в БД
def create_tables(engine):
    Base.metadata.drop_all(engine) # очищаем БД, чтобы не было конфликта
    Base.metadata.create_all(engine) # создаем таблицы в пустой БД