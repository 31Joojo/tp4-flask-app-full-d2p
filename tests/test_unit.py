# test_unit.py
### Modules importation
from datetime import datetime, timedelta, date
import pytest
from models import Task, User
from app import _build_postgres_uri

### First test : is_overdue() logic with different tests
### Test function : test_is_overdue_when_completed
def test_is_overdue_when_completed():
    """
    Should return False if a task is overdue.
    """
    t = Task()
    t.is_completed = True
    t.due_date = date.today() - timedelta(days=1)

    assert t.is_overdue() is False

### Test function : test_is_overdue_when_due_date_is_none
def test_is_overdue_when_due_date_is_none():
    """
    Should return False if the due date is None.
    """
    t = Task()
    t.is_completed = False
    t.due_date = None

    assert t.is_overdue() is False

### Tets function : test_is_overdue_when_due_date_is_in_past_not_completed
def test_is_overdue_when_due_date_is_in_past_not_completed():
    """
    Should return True if the due date is in the past and the task aren't completed.
    """
    t = Task()
    t.is_completed = False
    t.due_date = date.today() - timedelta(days=1)

    assert t.is_overdue() is True

### Second test : set_password() and check_password() methods
def test_user_password_hashing_and_check():
    """
    Should return True if the password is correct.
    """
    u = User()
    u.set_password("Tested_password")

    ### We test if the password is saved as a plaintext
    assert u.password_hash != "Tested_password"
    assert u.password_hash

    assert u.check_password("Tested_password") is True
    assert u.check_password("Wrong_password") is False

### Third test : environment parsing
### Function : test_build_postgres_uri
def test_build_postgres_uri(monkeypatch):
    """"
    Should return a valid postgresql uri with the connexion established.
    """
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "taskmanager")

    uri = _build_postgres_uri()

    # si ton helper encode le @, attends-toi à %40
    assert uri == "postgresql+psycopg2://postgres:test_password@localhost:5432/taskmanager"
