
Usage
=====

The library defines an ``EventManager`` to handle the session. This object can be passed a list of *brokers*, classes to which the events will be forwarded.

Basic
~~~~~

Import the events manager and instanciate it (synchronous API): ::

    from kosc_events import EventManager
    event_manager = EventManager(origin="mymodule")

The asynchronous version follows: ::
    event_manager = await EventManager.create(origin="mymodule")

``origin`` is meant to be an unique identifier of your library or module so that source of events can be tracked down.

The ``EventManager`` supports either synchronous or asynchronous APIs but not both at the same time. Have a look at the :ref:`api-desc` for details.

Synchronously send an event to the topic ``topic``: ::

    event_manager.push(topic, name, data=data)

Asynchrously send an event to the topic ``topic``: ::

    await event_manager.push_async(topic, name, data=data)


Brokers
~~~~~~~

Brokers can be of 2 types: ``persistent`` or ``message``.
Persistent brokers store the events for indexing (database-like storage) while message brokers are meant to deliver the events to other listeners (literally, message brokers).

You can pass a list of brokers to the ``EventManager``, for instance: ::

    event_manager = EventManager(
        origin="mymodule",
        brokers_list=[
            KafkaBroker(host="kfk-int"),
            StringIOBroker(stream="/tmp/events.log")
         ])

If ``brokers_list`` is not provided, the default brokers are instanciated: :ref:`api-desc-mongo` and :ref:`api-desc-kafka`, using environment variables for configuration.

See :ref:`api-desc` for more details.

Docker commands are provided to set-up the clusters required by some of the brokers.