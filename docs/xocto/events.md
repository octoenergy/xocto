# Events

## Application event logger

Used to write consistently formatted events to a logger, plus some extra utilities.

## Usage

```python
from xocto import events

events.publish(
    event="ACCOUNT.CREATED",
    params={
        'name': 'Barry Chuckle',
        'quote_id': 'xyz123',
    },
    meta={
        'account_id': 'A-12312345'
    },
    account=account,  # optional
    request=request,  # optional
)
```

## Event Timing

Time events using:

```python
from xocto import events

with events.Timer() as t:
    account = create_account()

events.publish(
    event="ACCOUNT.CREATED",
    params={
        'name': 'Barry Chuckle',
        'quote_id': 'xyz123',
    },
    meta={
        'account_id': account.account_id
        "duration_in_ms": t.duration_in_ms
    },
    account=account
)
```
