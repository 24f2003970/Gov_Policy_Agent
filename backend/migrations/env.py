from alembic import context
from app.config import Settings
from app.database import make_engine
from app.models import Base
from app import document_models
from app import index_models
from app import answer_models
from app import citation_models
from app import ocr_models

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
