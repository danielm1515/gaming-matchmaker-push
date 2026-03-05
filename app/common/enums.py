import enum


class SkillLevel(str, enum.Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    DIAMOND = "DIAMOND"
    MASTER = "MASTER"


SKILL_ORDER = {
    SkillLevel.BRONZE: 0,
    SkillLevel.SILVER: 1,
    SkillLevel.GOLD: 2,
    SkillLevel.PLATINUM: 3,
    SkillLevel.DIAMOND: 4,
    SkillLevel.MASTER: 5,
}


class AvailabilityStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    LOOKING_FOR_PARTY = "LOOKING_FOR_PARTY"
    IN_GAME = "IN_GAME"
    AWAY = "AWAY"
    OFFLINE = "OFFLINE"


class PartyStatus(str, enum.Enum):
    OPEN = "OPEN"
    FULL = "FULL"
    IN_GAME = "IN_GAME"
    DISBANDED = "DISBANDED"


class MessageType(str, enum.Enum):
    TEXT = "TEXT"
    SYSTEM = "SYSTEM"
    JOIN = "JOIN"
    LEAVE = "LEAVE"
