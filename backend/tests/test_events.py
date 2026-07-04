from app.events.base import Event
from app.events.dispatcher import EventDispatcher
from app.events.events import ProjectCreated


def test_global_handler_receives_every_event() -> None:
    dispatcher = EventDispatcher()
    received: list[Event] = []
    dispatcher.subscribe_all(received.append)

    event = ProjectCreated(project_id="p1", name="Report")
    dispatcher.publish(event)

    assert received == [event]


def test_typed_handler_only_receives_matching_event_type() -> None:
    dispatcher = EventDispatcher()
    project_created: list[ProjectCreated] = []
    dispatcher.subscribe(ProjectCreated, project_created.append)

    dispatcher.publish(ProjectCreated(project_id="p1", name="Report"))

    assert len(project_created) == 1
    assert project_created[0].project_id == "p1"
