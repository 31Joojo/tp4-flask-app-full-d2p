# test_integration.py
### Modules importation
from datetime import date, timedelta

from extensions import db
from models import Task, User


### ------------------------------ Helpers ------------------------------ ###
### Function : register
def register(client, username="test1", password="password1"):
    """
    Function to register a new user.
    """
    return client.post(
        "/register",
        data={"username": username, "password": password, "confirm": password},
        follow_redirects=True,
    )

### Function : login
def login(client, username, password):
    """
    Function to login a user.
    """
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )

### ------------------------- Integration tests ------------------------- ###
### First test : Register + login flow through the API
### Function : test_register_login_flow
def test_register_login_flow(client):
    """
    Test functionality of register and login.
    """
    ### First phase : checking registration flow
    r1 = register(client, "test1", "password1")
    assert r1.status_code == 200

    ### Second phase : checking login flow
    r2 = login(client, "test2", "password2")
    assert r2.status_code == 200

    ### We check if we get an element of the page after the login phase
    assert b"Logout" in r2.data or b"Task" in r2.data

### Second test : Creating a task via POST
### Function : test_create_task_via_post
def test_create_task(client):
    """
    Test functionality of create task via post.
    """
    ### Making a new registration for the test
    ### and we check if it has been stored correctly in the database
    resp_reg = register(client, "test3", "password3")
    with client.application.app_context():
        assert User.query.filter_by(username="test3").one_or_none() is not None, \
            resp_reg.data.decode("utf-8", errors="ignore")[:800]

    ### Login with the user info that just has been created
    ### and check it's right session of test3
    resp_login = login(client, "test3", "password3")
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None, \
            resp_login.data.decode("utf-8", errors="ignore")[:800]

    ### Creating a fake due date
    due = (date.today() + timedelta(days=10)).isoformat()

    ### Creating the task
    resp = client.post(
        "/tasks/new",
        data={"title": "Test task", "due_date": due},
        follow_redirects=True,
    )

    ### Testing if it has been created correctly
    assert resp.status_code == 200
    assert b"Login - Task Manager" not in resp.data

    ### We check the database to verify if the new data has been stored in it
    with client.application.app_context():
        t = Task.query.filter_by(title="Test task").one_or_none()
        assert t is not None

### Third test : Editing or toggling a task
### Function : test_toggle_task_completion
def test_toggle_task_completion(client):
    """
    Test functionality of toggle task completion.
    """
    ### Registration and login
    register(client, "test4", "password4")
    resp_login = login(client, "test4", "password4")

    ### We check if we're in the right session
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None, \
            resp_login.data.decode("utf-8", errors="ignore")[:800]

    ### We create the task directly in the database
    with client.application.app_context():
        ### Retrieving the user
        u = User.query.filter_by(username="test4").one()

        ### Creating the fake task
        task = Task(
            title="Toggle me",
            due_date=date.today(),
            is_completed=False,
            user_id=u.id,
        )

        ### Adding it into the database
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    ### Now we go on the toggle route
    resp = client.post(f"/tasks/{task_id}/toggle", follow_redirects=True)
    assert resp.status_code == 200

    ### We check again the database to verify if it's marked as complete
    with client.application.app_context():
        t = Task.query.get(task_id)
        assert t.is_completed is True
