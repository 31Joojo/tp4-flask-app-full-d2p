# test_integration.py
### Modules importation
from datetime import date, timedelta
import pytest
from extensions import db
from models import User, Task

### First test : Register + login flow through the API
### Function : register
def register(client, username="test1", password="password1"):
    """
    Register a new user.
    """
    return client.post(
        "/register",
        data={"username": username, "password": password, "confirm": password},
        follow_redirects=True,
    )

### Function : login
def login(client, username, password):
    """
    Login a user.
    """
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )

### Function : test_register_login_flow
def test_register_login_flow(client):
    """
    Test functionality of register and login.
    """
    r1 = register(client, "test1", "password1")
    assert r1.status_code == 200

    r2 = login(client, "test2", "password2")
    assert r2.status_code == 200

    ### We check if we get an element of the page after the login phase
    assert b"Logout" in r2.data or b"Task" in r2.data

### Second test : Creating a task via POST
### Function : test_create_task_via_post
def test_create_task_via_post(client):
    resp_reg = register(client, "test3", "password3")
    with client.application.app_context():
        assert User.query.filter_by(username="test3").one_or_none() is not None, \
            resp_reg.data.decode("utf-8", errors="ignore")[:800]

    resp_login = login(client, "test3", "password3")
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None, \
            resp_login.data.decode("utf-8", errors="ignore")[:800]

    due = (date.today() + timedelta(days=10)).isoformat()
    resp = client.post(
        "/tasks/new",
        data={"title": "Test task", "due_date": due},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Login - Task Manager" not in resp.data

    with client.application.app_context():
        t = Task.query.filter_by(title="Test task").one_or_none()
        assert t is not None

### Third test : Editing or toggling a task
### Function : test_toggle_task_completion
def test_toggle_task_completion(client):
    resp_reg = register(client, "test4", "password4")
    resp_login = login(client, "test4", "password4")

    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None, \
            resp_login.data.decode("utf-8", errors="ignore")[:800]

    with client.application.app_context():
        u = User.query.filter_by(username="test4").one()

        task = Task(
            title="Toggle me",
            due_date=date.today(),
            is_completed=False,
            user_id=u.id,
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    resp = client.post(f"/tasks/{task_id}/toggle", follow_redirects=True)
    assert resp.status_code == 200

    with client.application.app_context():
        t = Task.query.get(task_id)
        assert t.is_completed is True
