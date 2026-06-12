# Tests

This document describes how the test suite is structured, how to run it, and how to add new tests.

---

## Running Tests

From the pack root (`stackstorm-zabbix/`):

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_call_api.py -v

# Run a specific test
python3 -m pytest tests/test_find_object.py::FindObjectTestCase::test_find_single_host -v
```

### Prerequisites

- Python 3.12+
- Virtual environment with dependencies installed:

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes `st2common` (provides the test base class) and `zabbix-utils`.

---

## Architecture

### Path Setup

The `conftest.py` at the pack root adds `actions/` and `tests/` to `sys.path`. This mirrors how StackStorm resolves imports at runtime — action Python files import from `lib.actions` as a relative path, and tests import action classes directly by module name.

```python
# conftest.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'actions'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))
```

### Base Test Class

All tests extend `ZabbixBaseActionTestCase` (defined in `zabbix_base_action_test_case.py`):

```python
from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from my_action import MyAction

class MyActionTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = MyAction
```

This base class:
- Extends `st2tests.base.BaseActionTestCase` (provides `get_action_instance()`, `get_fixture_content()`)
- Loads fixture configs in `setUp()`: `self.full_config` and `self.blank_config`
- Provides `load_yaml()` and `load_json()` helpers for fixture files

### Key Attributes

| Attribute | Purpose |
|-----------|---------|
| `__test__ = True` | Tells pytest to collect this class (set `False` on base classes) |
| `action_cls = MyAction` | The action class under test — required by `get_action_instance()` |
| `self.full_config` | Valid Zabbix config (URL + credentials) loaded from `fixtures/full.yaml` |
| `self.blank_config` | Empty config — triggers `ValueError` on action instantiation |

---

## Fixtures

Located in `tests/fixtures/`:

| File | Purpose |
|------|---------|
| `full.yaml` | Symlink to `../../zabbix.yaml.example` — valid pack config with URL, username, password |
| `token.yaml` | Config with API token auth — tests token-based authentication path |
| `blank.yaml` | Empty YAML — used to test config validation errors |

Add new fixture files here for complex test scenarios (JSON responses, multi-host data, etc.).

---

## Test Patterns

### Pattern 1: Testing a dedicated Python action

```python
import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from my_action import MyAction

from zabbix_utils.exceptions import APIRequestError


class MyActionTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = MyAction

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_happy_path(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.return_value = [{'hostid': '10084'}]

        result = action.run(hostname='myhost')
        self.assertEqual(result, '10084')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_not_found_raises(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.return_value = []

        with self.assertRaises(ValueError):
            action.run(hostname='nonexistent')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_api_error_propagates(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.side_effect = APIRequestError('server error')

        with self.assertRaises(APIRequestError):
            action.run(hostname='myhost')
```

### Pattern 2: Testing connection failures

```python
@mock.patch('lib.actions.ZabbixBaseAction.connect')
def test_connection_error(self, mock_connect):
    action = self.get_action_instance(self.full_config)
    mock_connect.side_effect = ProcessingError('connection error')

    with self.assertRaises(ProcessingError):
        action.run(hostname='test')
```

### Pattern 3: Testing config validation

```python
def test_blank_config_raises(self):
    self.assertRaises(ValueError, self.action_cls, self.blank_config)
```

### Pattern 4: Mocking multi-level API calls

For `call_api.py` style tests where the API path is dotted (e.g. `host.get`):

```python
@mock.patch('lib.actions.ZabbixBaseAction.connect')
def test_dotted_method(self, mock_connect):
    action = self.get_action_instance(self.full_config)
    action.client = mock.Mock(spec=['host'])
    action.client.host = mock.Mock(spec=['get'])
    action.client.host.get.return_value = [{'hostid': '1'}]

    result = action.run(api_method='host.get', filter={'host': 'test'})
    self.assertEqual(result, [{'hostid': '1'}])
```

### Pattern 5: Testing helper methods on the base class

```python
@mock.patch('lib.actions.ZabbixAPI')
def test_find_host(self, mock_client):
    action = self.get_action_instance(self.full_config)
    mock_client.host.get.return_value = [{'hostid': '1', 'host': 'test'}]
    action.client = mock_client

    result = action.find_host('test')
    self.assertEqual(result, '1')
```

---

## Mocking Strategy

### Always mock `connect()`

Every test that calls `action.run()` must mock `ZabbixBaseAction.connect` to prevent real network calls:

```python
@mock.patch('lib.actions.ZabbixBaseAction.connect')
def test_something(self, mock_connect):
    ...
```

### Mock `self.client` directly

After mocking `connect()`, set `action.client` to a `mock.Mock()` to control API responses:

```python
action = self.get_action_instance(self.full_config)
action.client = mock.Mock()
action.client.host.get.return_value = [...]
```

### Mock helper methods when testing higher-level logic

If an action calls `self.find_host()`, mock it to isolate the test:

```python
action.find_host = mock.MagicMock(return_value='10084')
```

---

## What to Test

Each test file should cover:

| Category | What to Assert |
|----------|---------------|
| **Happy path** | Correct return value, correct API method called with expected args |
| **Not found** | `ValueError` raised when lookup yields no results |
| **Multiple found** | `ValueError` raised when unique lookup is ambiguous |
| **API errors** | `APIRequestError` propagates (or re-raises with context) |
| **Connection errors** | `ProcessingError` propagates |
| **Edge cases** | `None` parameters filtered, empty lists handled, boundary values |

### Coverage goals

- Every dedicated Python action file (`actions/*.py`) must have a corresponding `tests/test_*.py`
- YAML-only actions (using `call_api.py`) do NOT need individual tests — they are covered by `test_call_api.py` which validates the dispatcher logic
- Base class helpers are tested in `test_action_base.py`

---

## Adding a New Test File

1. Create `tests/test_<action_module>.py`
2. Import the action class and base test case:

```python
import mock
from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from my_action import MyAction
```

3. Define the test class:

```python
class MyActionTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = MyAction
```

4. Write tests covering happy path, error cases, and edge cases
5. Run and verify:

```bash
python3 -m pytest tests/test_my_action.py -v
```

---

## File Naming

| Convention | Example |
|------------|---------|
| Test file | `test_<python_module_name>.py` |
| Test class | `<ActionClass>TestCase` |
| Test method | `test_<behavior_being_tested>` |

The test filename maps to the Python entry point it tests, **not** the YAML action name. For example:
- `call_api.py` → `test_call_api.py`
- `find_object.py` → `test_find_object.py`
- `delete_host.py` → `test_delete_host.py`
