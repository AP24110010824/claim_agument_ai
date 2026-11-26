from flask_sqlalchemy import SQLAlchemy

# Standalone database instance (prevents circular imports)
db = SQLAlchemy()