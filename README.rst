corkscrew
=========

This is a python module that should eventually allow you to expose your
``peewee`` models through a JSON API compliant interface to HTTP
clients. For now it is under development and does not comply with all
aspects of the specification.

Installation
------------

Use ``pip install corkscrew`` to pull the module into your project. It
depends on ``peewee`` and ``bottle``.

Usage
-----

.. code:: python

    from corkscrew import BottleApplication
    from corkscrew.handlers import PeeweeHandlerFactory as PHF
    from peewee import Model, PrimaryKeyField, CharField, SqliteDatabase

    class Friends(Model):
      id = PrimaryKeyField()
      name = CharField()

      class Meta:
        database = SqliteDatabase(":memory:")

    Friends.create_table()

    application = BottleApplication(PHF)
    application.register(Friends)

    if __name__ == "__main__":
      application.run()
