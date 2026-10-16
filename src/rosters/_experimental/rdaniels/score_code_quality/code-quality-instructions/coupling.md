# Coupling

Coupling is the degree to which one module, class, or function depends on the
details of another. Useful evidence includes dependency direction, import and
call relationships, fan-out, cycles, shared mutable state, concrete types known
across boundaries, and how many components must change together.

Prefer small explicit interfaces and dependencies directed toward stable domain
concepts. High fan-in to a stable shared abstraction is not inherently bad, and
dependency count alone is not enough to judge quality. Give greater weight to
cycles, hidden dependencies, unrelated responsibilities, and knowledge of
another component's internals.

## Good example

```python
from typing import Protocol


class MessageSender(Protocol):
    def send(self, recipient: str, message: str) -> None: ...


def notify_user(sender: MessageSender, recipient: str) -> None:
    sender.send(recipient, "Your report is ready.")
```

The function depends only on the small capability it needs. The delivery
provider can change without changing the notification policy.

## Bad example

```python
def notify_user(app: Application, user_id: int) -> None:
    user = app.database.connection.users.find_internal_record(user_id)
    client = app.services.email.smtp_client
    client.send(app.settings.email.from_address, user.private_email, "Ready")
    app.services.audit.database.insert("notification_sent", user_id)
```

The function reaches through several objects, knows storage and provider
details, and mixes notification with auditing. Changes in multiple unrelated
components can break it.
