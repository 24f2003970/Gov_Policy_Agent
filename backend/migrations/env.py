from alembic import context
from app.config import Settings
from app.database import make_engine
from app.models import Base

target_metadata = Base.metadata

if context.is_offline_mode():
    raise RuntimeError("Use explicit online migrations; no secret connection strings are emitted")

connection = context.config.attributes.get("connection")
if connection is not None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(Settings())
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
