# Database Migration Guide (Alembic)

This guide explains how to manage database schema changes using Alembic.

## Quick Start

### 1. Initial Setup (One-time)
```bash
cd backend
alembic upgrade head
```

This applies all pending migrations to your database.

### 2. Creating a New Migration

When you make schema changes, create a migration:

```bash
cd backend
alembic revision -m "Description of changes"
```

This creates a new migration file in `migrations/versions/` with `upgrade()` and `downgrade()` functions.

### 3. Writing the Migration

Edit the generated migration file with your schema changes:

```python
def upgrade() -> None:
    """Upgrade schema."""
    # Add a new column
    op.add_column('users', sa.Column('email', sa.String(), nullable=False))
    
    # Create a new table
    op.create_table(
        'profiles',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False)
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('profiles')
    op.drop_column('users', 'email')
```

### 4. Apply Migrations

```bash
cd backend
alembic upgrade head
```

This applies all pending migrations.

## Common Tasks

### Check Current Schema Version
```bash
cd backend
alembic current
```

### View Pending Migrations
```bash
cd backend
alembic upgrade head --sql
```

### Downgrade to Previous Version
```bash
cd backend
alembic downgrade -1
```

### Downgrade All
```bash
cd backend
alembic downgrade base
```

## Environment Variables

The migrations use the following environment variables (in priority order):

1. **DATABASE_URL** - Full database connection string
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost/nexacore"
   ```

2. **Default** - SQLite at `./app.db`
   ```bash
   # No env var needed, falls back to sqlite:///./app.db
   ```

## Database Support

### PostgreSQL (Recommended for Production)
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/nexacore"
alembic upgrade head
```

### SQLite (Development)
```bash
# No env var needed
alembic upgrade head
```

### MySQL
```bash
export DATABASE_URL="mysql+pymysql://user:password@localhost/nexacore"
alembic upgrade head
```

## Docker Compose

To run migrations in Docker:

```bash
# In docker-compose.yml, add a migration service
docker-compose run --rm backend alembic upgrade head
```

Or in your Dockerfile:
```dockerfile
# Run migrations on startup
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0"]
```

## Best Practices

1. **Always test migrations locally first**
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```

2. **Make migrations reversible** - Always implement both `upgrade()` and `downgrade()`

3. **Keep migrations small** - One logical change per migration

4. **Use descriptive names** - `alembic revision -m "add_user_email_column"`

5. **Never edit applied migrations** - Create new migrations instead

6. **Version control** - Commit migrations to git

## Troubleshooting

### Migration Won't Apply
Check syntax:
```bash
cd backend
python -m alembic upgrade head --sql
```

### Need to Recreate Schema
```bash
# Downgrade to base (removes all tables)
alembic downgrade base

# Re-apply all migrations
alembic upgrade head
```

### PostgreSQL Specific Issues

If using PostgreSQL, ensure these are installed:
```bash
pip install psycopg2-binary
```

And export the DATABASE_URL:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/nexacore"
```

## Alembic Commands Reference

| Command | Purpose |
|---------|---------|
| `alembic init <directory>` | Initialize Alembic (one-time) |
| `alembic revision` | Create new migration (auto-generate stub) |
| `alembic upgrade <version>` | Apply migrations up to version |
| `alembic downgrade <version>` | Revert migrations down to version |
| `alembic current` | Show current schema version |
| `alembic heads` | Show all head revisions |
| `alembic branches` | Show all branch points |
| `alembic history` | Show migration history |
| `alembic stamp <version>` | Manually set schema version (dangerous!) |

## More Information

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Core Tutorial](https://docs.sqlalchemy.org/en/20/core/)
