"""Enumerations of the clean data contract (plan section 9.3). Values are upper-case strings."""
from enum import StrEnum


class ReportType(StrEnum):
    SPONTANEOUS = "SPONTANEOUS"
    STUDY = "STUDY"
    OTHER = "OTHER"


class ReporterQualification(StrEnum):
    PHYSICIAN = "PHYSICIAN"
    PHARMACIST = "PHARMACIST"
    OTHER_HEALTH_PROFESSIONAL = "OTHER_HEALTH_PROFESSIONAL"
    LAWYER = "LAWYER"
    CONSUMER = "CONSUMER"
    UNKNOWN = "UNKNOWN"


class Sex(StrEnum):
    FEMALE = "FEMALE"
    MALE = "MALE"
    UNKNOWN = "UNKNOWN"


class AgeGroup(StrEnum):
    A0_17 = "0-17"
    A18_44 = "18-44"
    A45_64 = "45-64"
    A65_74 = "65-74"
    A75_PLUS = "75+"
    UNKNOWN = "UNKNOWN"


class DrugRole(StrEnum):
    SUSPECT = "SUSPECT"
    CONCOMITANT = "CONCOMITANT"
    INTERACTING = "INTERACTING"
    OTHER = "OTHER"  # observed code 4 (E2B: drug not administered)


class MatchMethod(StrEnum):
    HARMONIZED = "HARMONIZED"
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    UNMATCHED = "UNMATCHED"


class ReactionOutcome(StrEnum):
    RECOVERED = "RECOVERED"
    RECOVERING = "RECOVERING"
    NOT_RECOVERED = "NOT_RECOVERED"
    RECOVERED_WITH_SEQUELAE = "RECOVERED_WITH_SEQUELAE"
    FATAL = "FATAL"
    UNKNOWN = "UNKNOWN"


class ShortageStatus(StrEnum):
    CURRENT = "CURRENT"
    TO_BE_DISCONTINUED = "TO_BE_DISCONTINUED"
    RESOLVED = "RESOLVED"


class Availability(StrEnum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class EventKind(StrEnum):
    APPEARED = "APPEARED"
    DISAPPEARED = "DISAPPEARED"
    STATUS_CHANGE = "STATUS_CHANGE"


class LinkStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    CANDIDATE = "CANDIDATE"
    UNREVIEWED = "UNREVIEWED"
    REJECTED = "REJECTED"


class LinkMethod(StrEnum):
    OPENFDA_RXCUI = "OPENFDA_RXCUI"
    NDC = "NDC"
    TEXT = "TEXT"


class KeyType(StrEnum):
    ACTIVESUBSTANCE = "ACTIVESUBSTANCE"
    MEDICINALPRODUCT = "MEDICINALPRODUCT"
    RECALL_TEXT = "RECALL_TEXT"


class RecallClass(StrEnum):
    CLASS_I = "CLASS_I"
    CLASS_II = "CLASS_II"
    CLASS_III = "CLASS_III"
    NOT_CLASSIFIED = "NOT_CLASSIFIED"


class RecallStatus(StrEnum):
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"
    UNKNOWN = "UNKNOWN"


class Tty(StrEnum):
    IN = "IN"
    MIN = "MIN"
    PIN = "PIN"
    SCD = "SCD"
    SBD = "SBD"
    BN = "BN"
    OTHER = "OTHER"


class LabelMatch(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NONE = "NONE"


class MatchType(StrEnum):
    SAME_INGREDIENT = "SAME_INGREDIENT"
    SAME_CLASS = "SAME_CLASS"


class SignalProfile(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class ProductType(StrEnum):
    RX = "RX"
    OTC = "OTC"
    OTHER = "OTHER"


class AlertType(StrEnum):
    SIGNAL = "SIGNAL"
    LABEL = "LABEL"
    SHORTAGE = "SHORTAGE"
    RECALL = "RECALL"


class RunType(StrEnum):
    FULL_LOAD = "FULL_LOAD"
    INCREMENTAL = "INCREMENTAL"
    SHORTAGE_POLL = "SHORTAGE_POLL"
    RECONCILIATION = "RECONCILIATION"


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


class RoleFilter(StrEnum):
    """Which drug roles count when building the 2x2 table."""
    SUSPECT = "SUSPECT"
    ALL = "ALL"
