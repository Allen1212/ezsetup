from app import app
import unittest
import json
from manage import create_root, delete_user
from typing import Tuple

test_client = app.test_client()

TEST_ADMIN_EMAIL = 'test_admin@gmail.com'
TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = '123456'

TEST_USER_EMAIL = 'test_user@gmail.com'
TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = '000000'

SECURITY_GROUP_RULES = [
    'egress ipv4 tcp 22 0.0.0.0/0',
    'ingress ipv4 tcp 22 0.0.0.0/0',
    'ingress ipv6 tcp 22 2001:0db8:85a3:0000:0000:8a2e:0370:7334/32',
    'ingress ipv4 tcp 8080 10.0.0.1',
    'ingress ipv4 tcp 8080-8090 10.0.0.1',
    'ingress ipv4 tcp 10.0.1.1',
    'ingress ipv4 tcp 8000-8010',
    'ingress ipv4 udp',
]

TOPO = {
    'instances': [
        {'id': 0, 'type': 'Instance', 'name': 'Instance0', 'x': 138.015625, 'y': 347},
        {'id': 1, 'type': 'Instance', 'name': 'Instance1', 'x': 534.015625, 'y': 416}
    ],
    'networks': [
        {'id': 0, 'type': 'NetworkNode', 'name': 'Network0', 'x': 409.015625, 'y': 105, 'cidr': '192.168.1.0/24'}
    ],
    'links': [
        {'id': 0, 'type': 'NetworkLink', 'name': 'Link0', 'networkId': 0, 'instanceId': 0, 'ip': '192.168.1.11'},
        {'id': 1, 'type': 'NetworkLink', 'name': 'Link1', 'networkId': 0, 'instanceId': 1, 'ip': '192.168.1.12'}
    ]
}


def _login(email: str, password: str) -> Tuple[str, str, str]:
    rv = test_client.post('/auth/tokens/', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'email': email,
        'password': password
    }))

    json_data = json.loads(rv.data)
    user_id = json_data['id']
    email = json_data['email']
    token = json_data['token']
    return user_id, email, token


def _signup_root_user():
    create_root(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, TEST_ADMIN_NAME)
    return _login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)


def _signup_test_user():
    create_root(TEST_USER_EMAIL, TEST_USER_PASSWORD, TEST_USER_NAME)
    return _login(TEST_USER_EMAIL, TEST_USER_PASSWORD)


def _delete_test_user(email):
    print("clean up ?".format(email))
    delete_user(email)


class AuthTestCase(unittest.TestCase):
    """Test case for /api/tokens/"""

    def setUp(self):
        self.addCleanup(_delete_test_user, TEST_ADMIN_EMAIL)
        self.user_id, self.email, self.token = _signup_root_user()

    def test_right_login(self):
        rv = test_client.post('/auth/tokens/', headers={
            'Content-Type': 'application/json',
        }, data=json.dumps({
            'email': self.email,
            'password': TEST_ADMIN_PASSWORD
        }))
        assert rv.status_code == 200
        json_data = json.loads(rv.data)
        assert json_data['email'] == TEST_ADMIN_EMAIL

    def test_wrong_login(self):
        rv = test_client.post('/auth/tokens/', headers={
            'Content-Type': 'application/json',
        }, data=json.dumps({
            'email': self.email,
            'password': '3u12oicpo'
        }))

        assert rv.status_code == 401
        json_data = json.loads(rv.data)
        assert json_data['error'] == 'email password mismatch'


class ScenarioTestCase(unittest.TestCase):
    """Test case for /api/scenarios/"""

    def setUp(self):
        self.addCleanup(_delete_test_user, TEST_ADMIN_EMAIL)
        self.user_id, self.email, self.token = _signup_root_user()

    def test_create_get_scenario(self):
        rv = test_client.post('/api/scenarios/', headers={
            'Content-Type': 'application/json',
            'Email': self.email,
            'Authorization': self.token
        }, data=json.dumps({
            'name': 'testScenario2',
            'description': 'ola',
            'sgRules': SECURITY_GROUP_RULES,
            'topo': TOPO,
            'isPublic': True
        }))

        duplicated_rv = test_client.post('/api/scenarios/', headers={
            'Content-Type': 'application/json',
            'Email': self.email,
            'Authorization': self.token
        }, data=json.dumps({
            'name': 'testScenario2',
            'description': 'ola',
            'sgRules': [],
            'topo': {
                'instances': [],
                'networks': [],
                'links': []
            },
            'isPublic': True
        }))

        assert rv.status_code == 200
        json_data = json.loads(rv.data)
        scenario_id = json_data['id']
        assert duplicated_rv.status_code == 409

        rv = test_client.get('/api/scenarios/', headers={
            'Content-Type': 'application/json',
            'Email': self.email,
            'Authorization': self.token
        })
        assert rv.status_code == 200
        json_data = json.loads(rv.data)
        assert len(json_data) == 1
        assert json_data[0]['id'] == scenario_id
        assert json_data[0]['name'] == 'testScenario2'
        assert json_data[0]['description'] == 'ola'
        assert json_data[0]['sgRules'] == SECURITY_GROUP_RULES


class LabTestCase(unittest.TestCase):
    """Test case for /api/labs/"""

    def setUp(self):
        self.addCleanup(_delete_test_user, TEST_ADMIN_EMAIL)
        self.user_id, self.email, self.token = _signup_root_user()

        # POST new scenario
        rv = test_client.post('/api/scenarios/', headers={
            'Content-Type': 'application/json',
            'Email': self.email,
            'Authorization': self.token
        }, data=json.dumps({
            'name': 'testScenario2',
            'description': 'ola',
            'sgRules': SECURITY_GROUP_RULES,
            'topo': TOPO,
            'isPublic': True
        }))
        json_data = json.loads(rv.data)
        self.scenario_id = json_data['id']

    def test_labs(self):
        rv = test_client.post('/api/labs/', headers={
            'Content-Type': 'application/json',
            'Email': self.email,
            'Authorization': self.token
        }, data=json.dumps({
            'name': 'testlab',
            'description': 'lab description',
            'scenarioId': self.scenario_id
        }))
        assert rv.status_code == 200


class UserAPITestCase(unittest.TestCase):
    """Test case for /api/users/"""

    def setUp(self):
        # root user signup
        self.addCleanup(_delete_test_user, TEST_ADMIN_EMAIL)
        self.root_id, self.root_email, self.root_token = _signup_root_user()
        # user signup
        self.addCleanup(_delete_test_user, TEST_USER_EMAIL)
        self.user_id, self.email, self.token = _signup_test_user()
