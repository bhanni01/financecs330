import pytest
from datetime import date
from app import app, db, User, Transaction


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def register(client, username='testuser', email='test@example.com', password='password123'):
    return client.post('/register', data={
        'username': username,
        'email': email,
        'password': password,
        'confirm_password': password,
    }, follow_redirects=True)


def login(client, email='test@example.com', password='password123'):
    return client.post('/login', data={
        'email': email,
        'password': password,
    }, follow_redirects=True)


def test_registration_hashes_password(client):
    register(client)
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.password != 'password123'
        assert user.password.startswith('$2b$')


def test_login_route_returns_200(client):
    response = client.get('/login')
    assert response.status_code == 200


def test_add_expense_persists_to_db(client):
    register(client)
    login(client)

    client.post('/add-transaction', data={
        'amount': '75.50',
        'type': 'expense',
        'category': 'Groceries',
        'date': '2024-01-15',
        'note': 'Weekly shopping',
    }, follow_redirects=True)

    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        txn = Transaction.query.filter_by(user_id=user.id).first()
        assert txn is not None
        assert txn.amount == 75.50
        assert txn.type == 'expense'
        assert txn.category == 'Groceries'


def test_duplicate_registration_rejected(client):
    register(client)
    response = register(client)
    # Template has no flash rendering, so verify rejection via DB state and re-render (200, not redirect)
    assert response.status_code == 200
    with app.app_context():
        count = User.query.filter_by(email='test@example.com').count()
        assert count == 1
