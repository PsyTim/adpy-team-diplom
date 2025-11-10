import sqlalchemy
from sqlalchemy.orm import sessionmaker

from db.models import create_tables

# строка для подключения к источнику данных(в нашем случае БД) в формате - ДРАЙВЕР_ПОДКЛЮЧЕНИЯ://ЛОГИН:ПАРОЛЬ@ХОСТ:ПОРТ/НАЗВАНИЕ_БД
DSN = '' # ХОСТ localhost:5432 если запуск со своего ПК
engine = sqlalchemy.create_engine(DSN) # переменная для поключения к БД, когда ее об этом просят
create_tables(engine) # создаем таблицы в БД
Session = sessionmaker(bind=engine) # создаем сессию
session = Session() # создаем экземпляр класса сессии

session.close()  # закрываем сессию