# test_e2e.py
### Moules importation
import os
import threading
from datetime import date, timedelta
from uuid import uuid4
import pytest
from werkzeug.serving import make_server
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from app import create_app
from extensions import db


# ---------- Fixtures: serveur Flask live + navigateur Selenium ----------
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
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")

    d = webdriver.Chrome(options=options)
    d.implicitly_wait(1)
    yield d
    d.quit()

def submit_first_form(driver, timeout=5):
    # On soumet le 1er form
    form = driver.find_element(By.TAG_NAME, "form")
    current_url = driver.current_url
    form.submit()

    # Attente robuste: l'URL change (redirect) OU on n'est plus sur la même page
    def _moved(d):
        try:
            return d.current_url != current_url
        except StaleElementReferenceException:
            return True

    WebDriverWait(driver, timeout).until(_moved)

def ui_register(driver, base_url, username, password):
    driver.get(f"{base_url}/register")

    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)

    # Certains projets demandent une confirmation avec un nom variable
    for cand in ["confirm_password", "password_confirm", "confirm", "password2"]:
        try:
            driver.find_element(By.NAME, cand).send_keys(password)
            break
        except Exception:
            pass

    submit_first_form(driver)

    # Si register marche, tu quittes /register (souvent redirect vers /login)
    WebDriverWait(driver, 5).until(lambda d: "/register" not in d.current_url)

def ui_login(driver, base_url, username, password):
    driver.get(f"{base_url}/login")
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "username")))

    driver.find_element(By.NAME, "username").clear()
    driver.find_element(By.NAME, "username").send_keys(username)

    driver.find_element(By.NAME, "password").clear()
    driver.find_element(By.NAME, "password").send_keys(password)

    submit_first_form(driver)

    WebDriverWait(driver, 5).until(lambda d: "/login" not in d.current_url)


### Function : ui_create_task
def ui_create_task(driver, base_url, title, description="", due_date_iso=None):
    driver.get(f"{base_url}/tasks/new")

    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "title")))

    driver.find_element(By.NAME, "title").clear()
    driver.find_element(By.NAME, "title").send_keys(title)

    if description:
        desc = driver.find_element(By.NAME, "description")
        desc.clear()
        desc.send_keys(description)

    if due_date_iso:
        due_el = driver.find_element(By.NAME, "due_date")
        # set via JS (très fiable pour <input type="date">)
        driver.execute_script("arguments[0].value = arguments[1];", due_el, due_date_iso)

    # Clique sur le bouton "Save" (vu sur tes captures)
    save_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Save' or @type='submit']")
    save_btn.click()

    # Attendre que la création soit confirmée
    WebDriverWait(driver, 8).until(
        lambda d: "Task created." in d.find_element(By.TAG_NAME, "body").text
                  or "Your Tasks" in d.find_element(By.TAG_NAME, "body").text
    )

    # Assure qu'on est bien sur la liste
    driver.get(f"{base_url}/")
    WebDriverWait(driver, 5).until(lambda d: "Your Tasks" in d.find_element(By.TAG_NAME, "body").text)


def find_task_card(driver, title):
    # Ton template semble utiliser .task-item (vu le CSS) -> on s'appuie dessus
    return driver.find_element(By.XPATH, f"//*[contains(@class,'task-item')][contains(., '{title}')]")

def wait_task_visible(driver, title, timeout=8):
    WebDriverWait(driver, timeout).until(
        lambda d: title in d.find_element(By.TAG_NAME, "body").text
    )

# ---------- Tests E2E demandés ----------

def test_e2e_login_redirect(driver, live_server):
    base_url, _ = live_server

    username = f"user_{uuid4().hex[:8]}"
    password = "password123"

    ui_register(driver, base_url, username, password)
    ui_login(driver, base_url, username, password)

    # Vérifie qu'on n'est plus sur la page login
    WebDriverWait(driver, 5).until(lambda d: "/login" not in d.current_url)


def test_e2e_create_task_appears_in_ui(driver, live_server):
    base_url, _ = live_server

    username = f"user_{uuid4().hex[:8]}"
    password = "password123"
    task_title = f"Task_{uuid4().hex[:8]}"

    ui_register(driver, base_url, username, password)
    ui_login(driver, base_url, username, password)

    due = (date.today() + timedelta(days=10)).isoformat()
    ui_create_task(driver, base_url, task_title, description="hello", due_date_iso=due)

    # On est maintenant sur "/", on attend l'item
    wait_task_visible(driver, task_title, timeout=8)
    assert task_title in driver.find_element(By.TAG_NAME, "body").text


def test_e2e_toggle_or_delete_task(driver, live_server):
    base_url, _ = live_server

    username = f"user_{uuid4().hex[:8]}"
    password = "password123"
    task_title = f"Task_{uuid4().hex[:8]}"

    ui_register(driver, base_url, username, password)
    ui_login(driver, base_url, username, password)

    ui_create_task(driver, base_url, task_title, due_date_iso=date.today().isoformat())

    wait_task_visible(driver, task_title, timeout=8)

    # Trouver la "card" qui contient le titre
    card = WebDriverWait(driver, 8).until(
        EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(., '{task_title}')][.//button[normalize-space()='Delete']]")
        )
    )
    delete_btn = card.find_element(By.XPATH, ".//button[normalize-space()='Delete']")
    delete_btn.click()

    # Accepter la popup "Delete this task?"
    WebDriverWait(driver, 5).until(EC.alert_is_present())
    driver.switch_to.alert.accept()

    WebDriverWait(driver, 8).until(
        lambda d: "Task deleted." in d.find_element(By.TAG_NAME, "body").text
    )
    WebDriverWait(driver, 8).until(
        lambda d: task_title not in d.find_element(By.TAG_NAME, "body").text
    )
