# conftest.py
### Modules importation
import os
import pytest
from app import create_app
from extensions import db


### Function : flask_app
@pytest.fixture()
def flask_app():
    """
    Function to create a flask app
    """
    ### Environment variables
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "test_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB_TEST", "taskmanager_test")

    ### Creating our app
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{user}:{password}@{host}:{port}/{name}"

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


### Function : client
@pytest.fixture()
def client(flask_app):
    """
    Function to create a flask app
    """
    with flask_app.test_client() as c:
        yield c

