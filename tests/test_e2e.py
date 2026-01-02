# test_e2e.py
### Moules importation
import os
import threading
from datetime import date, timedelta
from uuid import uuid4

import pytest
from app import create_app
from extensions import db
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from werkzeug.serving import make_server


### ------------ Flask live server and Selenium browser setup ----------- ###
### Function : live_server
@pytest.fixture(scope="session")
def live_server():
    """
    Start the Flask app on a free port for E2E testing.
    """
    ### Environment variables for E2E DB
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "pass")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB_E2E", "taskmanager_e2e")

    ### Creating the flask app with create_app()
    app = create_app()
    app.config.update(TESTING=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    app.config["SECRET_KEY"] = "123456ABCDEF"

    with app.app_context():
        db.drop_all()
        db.create_all()

    ### Defining :
    ### the server
    server = make_server("127.0.0.1", 0, app)

    ### the port
    port = server.server_port

    ### launch the server within a daemon thread
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    yield base_url, app

    ### Shutting down the server
    server.shutdown()
    thread.join()

    ### Cleaning the database
    with app.app_context():
        db.session.remove()
        db.drop_all()

### Function : driver
@pytest.fixture()
def driver():
    """
    Provide a Selenium browser for each test
    """
    ### Chrome driver configuration
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")

    ### Chrom driver Instantiation
    d = webdriver.Chrome(options=options)
    d.implicitly_wait(1)

    ### The test will use the driver
    yield d

    ### Chrome closure
    d.quit()

### Function : submit_first_form
def submit_first_form(driver, timeout=5):
    """
    Submit the first form on the login page and wait for a clean redirect.
    """
    ### We send the first form
    form = driver.find_element(By.TAG_NAME, "form")
    current_url = driver.current_url
    form.submit()

    ### Subfunction : _moved
    def _moved(d):
        """
        Subfunction for robust waiting to detect if the URL changes or
        if we are no longer on the same page
        """
        try:
            return d.current_url != current_url
        except StaleElementReferenceException:
            return True

    WebDriverWait(driver, timeout).until(_moved)

### Function : ui_register
def ui_register(driver, base_url, username, password):
    """
    Mimic a user registration via the UI.
    """
    ### Here we go on the register page
    driver.get(f"{base_url}/register")

    ### Filling the form to register a new user
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)

    ### Filling again the password to confirm it
    try:
        driver.find_element(By.NAME, "confirm").send_keys(password)
    except Exception:
        pass

    ### Submitting the form
    submit_first_form(driver)

    ### We wait to see if the registration worked and then we're redirected
    ### to the login page
    WebDriverWait(driver, 5).until(lambda d: "/register" not in d.current_url)

### Function : ui_login
def ui_login(driver, base_url, username, password):
    """
    Mimic a login via the user interface.
    """
    ### Here we go on the login page
    driver.get(f"{base_url}/login")

    ### Wait until the username field exists so
    ### it understands that the page is ready
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located(
            (By.NAME, "username")
        )
    )

    ### Clearing the form and filling it
    driver.find_element(By.NAME, "username").clear()
    driver.find_element(By.NAME, "username").send_keys(username)

    driver.find_element(By.NAME, "password").clear()
    driver.find_element(By.NAME, "password").send_keys(password)

    ### Submitting the form
    submit_first_form(driver)

    ### We wait to see if the login worked
    ### and then we're redirected to the home page
    WebDriverWait(driver, 5).until(lambda d: "/login" not in d.current_url)

### Function : ui_create_task
def ui_create_task(driver, base_url, title, description="", due_date_iso=None):
    """
    Mimic a task creation via the user interface.
    """
    ### Here we go on the page to create a new task
    driver.get(f"{base_url}/tasks/new")

    ### We wait for the title field to appear
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "title")))

    ### Clearing and filling the new task title
    driver.find_element(By.NAME, "title").clear()
    driver.find_element(By.NAME, "title").send_keys(title)

    ### Adding a description
    if description:
        desc = driver.find_element(By.NAME, "description")
        desc.clear()
        desc.send_keys(description)

    ### Adding a due date
    if due_date_iso:
        due_el = driver.find_element(By.NAME, "due_date")
        driver.execute_script(
            "arguments[0].value = arguments[1];",
            due_el,
            due_date_iso
        )

    ### Then the modifications are saved
    save_btn = driver.find_element(
        By.XPATH,
        "//button[normalize-space()='Save' or @type='submit']"
    )
    save_btn.click()

    ### We wait for the task to be created and added in the database
    WebDriverWait(driver, 8).until(
        lambda d: "Task created." in d.find_element(By.TAG_NAME, "body").text
                  or "Your Tasks" in d.find_element(By.TAG_NAME, "body").text
    )

    ### After we go back on the home page where all the tasks are listed
    driver.get(f"{base_url}/")
    WebDriverWait(driver, 5).until(
        lambda d: "Your Tasks" in d.find_element(By.TAG_NAME, "body").text
    )

### Function : find_task_card
def find_task_card(driver, title):
    """
    Find a task item containing the title in the list.
    """
    return driver.find_element(
        By.XPATH,
        f"//*[contains(@class,'task-item')][contains(., '{title}')]"
    )

### Function : wait_task_visible
def wait_task_visible(driver, title, timeout=8):
    """
    Function to wait until the task title appears in the page text.
    """
    WebDriverWait(driver, timeout).until(
        lambda d: title in d.find_element(By.TAG_NAME, "body").text
    )

### -------------------------- End-2-end tests -------------------------- ###
### First test : visit login page and redirection
### Function : test_e2e_login_redirect
def test_e2e_login_redirect(driver, live_server):
    """
    Function to check the register, login, and redirect flow
    """
    base_url, _ = live_server

    ### Creating fake user info
    username = f"user_{uuid4().hex[:8]}"
    password = "password123"

    ### Making a user registration
    ui_register(driver, base_url, username, password)

    ### Login with the user info we've just created
    ui_login(driver, base_url, username, password)

    ### Then we test if we're not on the login
    WebDriverWait(driver, 5).until(lambda d: "/login" not in d.current_url)

### Second test : create task through UI
### Function : test_e2e_create_task_appears_in_ui
def test_e2e_create_task(driver, live_server):
    """
    Function to check the task creation appears in the UI.
    """
    base_url, _ = live_server

    ### Creating fake user info and a fake task
    username = f"user_{uuid4().hex[:8]}"
    password = "password123"
    task_title = f"Task_{uuid4().hex[:8]}"

    ### Making a user registration
    ui_register(driver, base_url, username, password)

    ### Login with the user info we've just created
    ui_login(driver, base_url, username, password)

    ### Adding a fake due date
    due = (date.today() + timedelta(days=10)).isoformat()

    ### Creating a fake new task
    ui_create_task(driver, base_url, task_title, description="hello", due_date_iso=due)

    ### Now we're on the home page and wait for the new task created to be visible
    wait_task_visible(driver, task_title, timeout=8)
    assert task_title in driver.find_element(By.TAG_NAME, "body").text

### Third test : toggle or delete task through UI
### Function : test_e2e_toggle_delete_task
def test_e2e_toggle_delete_task(driver, live_server):
    """
    Function to check the toggle or delete task appears in the UI.
    """
    base_url, _ = live_server

    ### Creating fake user info and a fake task
    username = f"user_{uuid4().hex[:8]}"
    password = "password123"
    task_title = f"Task_{uuid4().hex[:8]}"

    ### Making a user registration
    ui_register(driver, base_url, username, password)

    ### Login with the user info we've just created
    ui_login(driver, base_url, username, password)

    ### Creating a fake new task
    ui_create_task(driver, base_url, task_title, due_date_iso=date.today().isoformat())

    ### We're on the home page and wait for the new task created to be visible
    wait_task_visible(driver, task_title, timeout=8)

    ### Find the card that contains the title
    card = WebDriverWait(driver, 8).until(
        EC.presence_of_element_located(
            (By.XPATH,
             f"//*[contains(., '{task_title}')][.//button[normalize-space()='Delete']]")
        )
    )

    ### Mimic the click on delete button to delete the task
    delete_btn = card.find_element(By.XPATH, ".//button[normalize-space()='Delete']")
    delete_btn.click()

    ### Accept the popup to delete this task
    WebDriverWait(driver, 5).until(EC.alert_is_present())
    driver.switch_to.alert.accept()

    ### Now we wait for "task deleted" to be displayed on the home page
    ### confirm it has been deleted
    WebDriverWait(driver, 8).until(
        lambda d: "Task deleted." in d.find_element(By.TAG_NAME, "body").text
    )

    ### We also check if the task is no more present on the page
    WebDriverWait(driver, 8).until(
        lambda d: task_title not in d.find_element(By.TAG_NAME, "body").text
    )
