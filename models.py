import uuid
from datetime import datetime, timezone
from database import db


class Claim(db.Model):
    """
    Primary Claims Table: Stores root claim metadata and cryptographic hash.
    """
    __tablename__ = "claims"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    status = db.Column(db.String(16), default="COMPLETED", nullable=False)
    adjuster_notes = db.Column(db.Text, nullable=True)
    source_image_hash = db.Column(db.String(64), nullable=False)
    source_image_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relational Navigation with Cascade Cleanups
    assessment = db.relationship("DamageAssessment", backref="claim", uselist=False, cascade="all, delete-orphan")
    augmented_photos = db.relationship("AugmentedPhoto", backref="claim", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "claim_number": self.claim_number,
            "status": self.status,
            "adjuster_notes": self.adjuster_notes,
            "source_image_hash": self.source_image_hash,
            "source_image_url": f"/uploads/{self.source_image_path}",
            "created_at": self.created_at.isoformat(),
            "assessment": self.assessment.to_dict() if self.assessment else None,
            "augmented_photos": [photo.to_dict() for photo in self.augmented_photos]
        }


class DamageAssessment(db.Model):
    """
    Damage Assessment Table: Stores Groq AI classification and actuarial financial calculations.
    """
    __tablename__ = "damage_assessments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    claim_id = db.Column(db.String(36), db.ForeignKey("claims.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    damage_type = db.Column(db.String(32), nullable=False)
    severity = db.Column(db.String(16), nullable=False)
    estimated_action = db.Column(db.String(32), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.String(32), nullable=False)
    labor_hours = db.Column(db.String(32), nullable=False)
    parts_cost = db.Column(db.String(32), nullable=False)
    total_loss_probability = db.Column(db.String(16), nullable=False)
    summary = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "damage_type": self.damage_type,
            "severity": self.severity,
            "estimated_action": self.estimated_action,
            "confidence_score": self.confidence_score,
            "total_cost": self.total_cost,
            "labor_hours": self.labor_hours,
            "parts_cost": self.parts_cost,
            "total_loss_probability": self.total_loss_probability,
            "summary": self.summary
        }


class AugmentedPhoto(db.Model):
    """
    Augmented Photos Table: Stores individual synthetic variations with provenance.
    """
    __tablename__ = "augmented_photos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    claim_id = db.Column(db.String(36), db.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    
    effect_type = db.Column(db.String(32), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            "effect": self.effect_type,
            "filename": self.filename,
            "url": f"/uploads/{self.filename}"
        }