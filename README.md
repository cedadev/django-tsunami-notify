# django-tsunami-notify

This Django app provides functionality for sending notifications that are associated with
[Tsunami events](https://github.com/cedadev/django-tsunami.git).

## Installation

This package can be installed directly from GitHub:

```sh
pip install git+https://github.com/cedadev/django-tsunami-notify.git
```

Once installed, add the app to your `INSTALLED_APPS` alongside Tsunami:

```python
INSTALLED_APPS = [
    # ... other apps ...
    'tsunami',
    'tsunami_notify',
]
```

You will need to make sure your
[email settings](https://docs.djangoproject.com/en/stable/topics/email/) are configured
appropriately for your environment.

By default, notifications will use the value of the
[DEFAULT_FROM_EMAIL setting](https://docs.djangoproject.com/en/stable/ref/settings/#default-from-email).
However if required, you can specify an email address specifically to be used as the
`From` address for notifications:

```python
TSUNAMI_NOTIFY_FROM_EMAIL = "support@jasmin.ac.uk"
```

## Usage

Notifications are sent by creating instances of the `Notification` model. A notification
consists of the following fields:

<dl>
    <dt><code>event</code></dt>
    <dd><p>The Tsunami event that triggered the notification.</p></dd>
    <dt><code>email</code></dt>
    <dd><p>The email address that the notification should be sent to.</p></dd>
    <dt><code>context</code></dt>
    <dd>
        <p>A dictionary containing extra template context for the notification.</p>
        <p>Must be JSON-serializable.</p>
    </dd>
    <dt><code>sent_at</code></dt>
    <dd><p>The <code>datetime</code> at which the notification was last successfully sent.</p></dd>
    <dt><code>created_at</code></dt>
    <dd><p>The <code>datetime</code> at which the notification was created.</p></dd>
</dl>

The `Notification` model provides a helper class method:

```python
notification = Notification.create(event, "joe.bloggs@example.com")

notification_with_context = Notification.create(
    event,
    "jane.doe@example.org",
    { "role": "OWNER" }
)
```

Notifications are **not** created automatically in response to events, as it is not possible
to automatically infer what email addresses a notification should be created for.
Developers should use the functionality provided by Tsunami for
[listening to events](https://github.com/cedadev/django-tsunami#listening-to-events) and
create `Notification` objects in their event handlers:

```python
from tsunami.helpers import model_event_listener
from tsunami_notify.models import Notification

# Assume we have a Project model with a ManyToMany field to users
from .models import Project


@model_event_listener(Project, ['updated'])
def notify_project_users_when_updated(event):
    """
    Notify the project users when a project is updated.
    """
    # The event target is the project
    users = event.target.users.all()
    for user in users:
        Notification.create(
            event,
            user.email,
            dict(extra_context = "some extra context")
        )
```

### Notification templates

The content for the subject and body of notifications is determined by rendering
[templates](https://docs.djangoproject.com/en/stable/topics/templates/). The locations
of the templates that the notification will use is determined by the type of the event
that the notification is for.

Notification templates live in the `templates/tsunami_notify` directory inside your app.
Within that directory it will look for templates for a notification in the following
directories:

  * A directory named after the event type.
  * Nested directories where the names of the nested directories are determined by
    splitting the event type on dots.

For example, for a notification whose event has type `myapp.mymodel.updated` the
following directories will be searched:

  * `templates/tsunami_notify/myapp.mymodel.updated/`
  * `templates/tsunami_notify/myapp/mymodel/updated/`

Within the directory for an event type, the following templates are used:

  * `subject.txt`: Renders the subject line for the notification.
  * `message.txt`: Renders the plain-text body for the notification.
  * `message.html` (OPTIONAL): If present, renders the HTML part of a `multipart/alternative`
    email. If not present, notifications are sent as plain-text only.

Each template will receive the following context:

  * `event`: The event for the notification.
  * `target`: The target of the event.
  * `recipient`: The user that is the recipient of the notification, if the email
    address corresponds to a known user.
  * Extra context specified when the notification was created.

### Admin integration

This package includes a `ModelAdmin` for the `Notification` model that is automatically
registered with the default admin site. The admin integration can be used to filter and
inspect the state of notifications, and also includes an admin action to (re-)send
selected notifications.

### Management command

This package includes a management command that, when executed, will attempt to send any
notifications that have not been successfully sent before:

```sh
# If DJANGO_SETTINGS_MODULE environment variable is set
django-admin sendnotifications

# Or using manage.py
python manage.py sendnotifications
```

Rather than sending notifications during an HTTP request, this management command can
be executed on a regular basis to send unsent notifications. This has two main benefits:

  * Any exceptions raised while sending a notification will not cause a request
    to return a 500 error.
  * Any notifications that fail to send will be tried again the next time the
    management command is run.

The frequency that the command is run at will depend on how urgent your emails are.
For a system that only has passive notifications, e.g. notifying a user that another user
has done something that they might want to be aware of, every 5 minutes might be OK.
However for a system that needs to send a notification during a user interaction,
a shorter timeframe might be more appropriate.

If your application has mostly passive notifications but has particular types of notification
that must be sent quickly (e.g. an email containing a code for a two-factor authentication
system), you could use a longer duration for the management command but attempt to send
those specific notifications programmatically within the request (i.e. as soon as they are
created). If you do this, you must catch exceptions when sending the notification within
the request to prevent the request from returning a 500 error. The advantage of still
creating a notification in this case is that if the initial send fails, the management
command will retry it the next time it runs.

### Sending notifications programmatically

Once created, notifications can be sent by calling the `send` method:

```python
notification.send()
```

If the notification has already been sent successfully, this will resend it.

It is also possible to send multiple notifications at once from a `QuerySet`. This
has the advantage of reusing the same SMTP connection for all notifications. For
example, the following will resend all the notifications ever created for the
specified email address:

```python
Notification.objects.filter(email = "joe.bloggs@example.com").send_all()
```
