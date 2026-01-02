# test_unit.py
### Modules importation
from datetime import date, timedelta

from app import _build_postgres_uri
from models import Task, User


### ----------------------------- Unit tests ---------------------------- ###
### First test : is_overdue()
### Function : test_is_overdue_when_completed
def test_is_overdue_when_completed():
    """
    Should return False if a task is overdue.
    """
    ### We create a fake task
    t = Task()
    ### mark it as completed
    t.is_completed = True
    ### add a fake due date
    t.due_date = date.today() - timedelta(days=1)

    assert t.is_overdue() is False

### Function : test_is_overdue_when_due_date_is_none
def test_is_overdue_when_due_date_is_none():
    """
    Should return False if the due date is None.
    """
    ### We create a fake task
    t = Task()
    ### mark it as not completed
    t.is_completed = False
    ### set the due date as none
    t.due_date = None

    ### Then we test whether due_date is None and should return False directly
    assert t.is_overdue() is False

### Fnuction : test_is_overdue_when_due_date_is_in_past_not_completed
def test_is_overdue_when_due_date_is_past_not_completed():
    """
    Should return True if the due date is in the past and the task aren't completed.
    """
    ### We create a fake task
    t = Task()
    ### mark it as not completed
    t.is_completed = False
    ### add a fake due date
    t.due_date = date.today() - timedelta(days=1)

    ### Now we test case when the task is incomplete and the date has passed
    assert t.is_overdue() is True

### Second test : set_password() and check_password() methods
### Function : test_user_password_hashing_and_check
def test_user_password_hashing_and_check():
    """
    Should return True if the password is correct.
    """
    u = User()
    u.set_password("Tested_password")

    ### We test if the password is saved as a plaintext
    assert u.password_hash != "Tested_password"
    ### Now if the hashed password exists
    assert u.password_hash

    ### Now it tests if it's the right or wrong password
    assert u.check_password("Tested_password") is True
    assert u.check_password("Wrong_password") is False

### Third test : environment parsing
### Function : test_build_postgres_uri
def test_build_postgres_uri(monkeypatch):
    """"
    Should return a valid postgresql uri with the connexion established.
    """
    ### Loading the environment variables
    ### force the branch that uses POSTGRES_ variables
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "taskmanager")

    uri = _build_postgres_uri()

    ### We verify the environment parsing with the environment variables loaded
    assert uri == "postgresql://postgres:test_password@localhost:5432/taskmanager"
