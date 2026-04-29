import pytest
import json
import sys
sys.path.insert(0, '/app')

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    yield client


class TestPages:
    def test_login_page_loads(self, client):
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_register_page_loads(self, client):
        response = client.get('/register')
        assert response.status_code == 200
        assert b'register' in response.data.lower()

    def test_profile_page_requires_login(self, client):
        response = client.get('/profile')
        assert response.status_code == 302

    def test_index_page_requires_login(self, client):
        response = client.get('/')
        assert response.status_code == 302

    def test_profile_page_works(self, authenticated_client):
        response = authenticated_client.get('/profile')
        assert response.status_code == 200


class TestAPI:
    def test_recommendations_requires_login(self, client):
        response = client.post('/api/recommendations', json={})
        assert response.status_code == 302

    def test_tags_api_requires_login(self, client):
        response = client.get('/api/tags')
        assert response.status_code == 302

    def test_geoprofiles_api_requires_login(self, client):
        response = client.get('/api/geoprofiles')
        assert response.status_code == 302

    def test_search_mode_api_requires_login(self, client):
        response = client.get('/api/search-mode')
        assert response.status_code == 302

    def test_search_requires_login(self, client):
        response = client.post('/api/search', json={})
        assert response.status_code == 302


class TestAPIWithAuth:
    def test_recommendations_no_interests(self, authenticated_client):
        response = authenticated_client.post('/api/recommendations', json={})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'items' in data

    def test_search_mode_get(self, authenticated_client):
        response = authenticated_client.get('/api/search-mode')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data in ('nearby', 'balanced', 'interests')

    def test_search_mode_set(self, authenticated_client):
        response = authenticated_client.post('/api/search-mode', json={'mode': 'interests'})
        assert response.status_code == 200

    def test_search_empty_query(self, authenticated_client):
        response = authenticated_client.post('/api/search', json={'query': ''})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'items' in data

    def test_geoprofiles_get(self, authenticated_client):
        response = authenticated_client.get('/api/geoprofiles')
        assert response.status_code == 200

    def test_geoprofiles_active_get(self, authenticated_client):
        response = authenticated_client.get('/api/geoprofiles/active')
        assert response.status_code == 200


class TestTrackedEvents:
    def test_tracked_page_requires_login(self, client):
        response = client.get('/tracked')
        assert response.status_code == 302

    def test_tracked_page_works(self, authenticated_client):
        response = authenticated_client.get('/tracked')
        assert response.status_code == 200


class TestEventPage:
    def test_event_page_requires_login(self, client):
        response = client.get('/event/1')
        assert response.status_code == 302


class TestInterests:
    def test_interests_page_requires_login(self, client):
        response = client.get('/select-interests')
        assert response.status_code == 302

    def test_interests_page_works(self, authenticated_client):
        response = authenticated_client.get('/select-interests')
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])