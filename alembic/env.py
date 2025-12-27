import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context


# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(dotenv_path=r"C:\Users\ghara\OneDrive\Desktop\parth\auroraa sentinal\.env")

# Ensure Alembic can find app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import your Base and models
from app.database.database import Base
from app.models.models import Watermark

# Alembic Config object
config = context.config

# 🔗 Inject DATABASE_URL into alembic config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate'
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    print(f"⚙️ Offline mode: using {url}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        print(f"✅ Online mode: connected to {connection.engine.url}")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

# Entry point
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

