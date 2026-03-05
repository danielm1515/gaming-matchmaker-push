import uuid
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.parties.models import Party, PartyMember
from app.players.models import Player, PlayerGame
from app.common.enums import PartyStatus, AvailabilityStatus, SKILL_ORDER, SkillLevel

# Neighboring regions for soft region bonus
NEIGHBORING_REGIONS: dict[str, set[str]] = {
    "EU": {"EUNE", "ME"},
    "EUNE": {"EU", "ME"},
    "NA": {"LATAM"},
    "LATAM": {"NA"},
    "ME": {"EU", "EUNE"},
    "OCE": {"SEA"},
    "SEA": {"OCE"},
}


@dataclass
class MatchResult:
    party: Party
    match_score: int
    region_score: int
    skill_score: int
    fill_score: int
    availability_score: int


async def find_matches(
    player: Player,
    game_id: uuid.UUID,
    db: AsyncSession,
    max_skill_distance: int = 2,
    limit: int = 10,
) -> list[MatchResult]:
    player_skill_rank = SKILL_ORDER[player.skill_level]

    # Fetch candidate parties
    q = (
        select(Party)
        .options(
            selectinload(Party.game),
            selectinload(Party.region),
            selectinload(Party.leader).selectinload(Player.region),
            selectinload(Party.leader).selectinload(Player.player_games).selectinload(PlayerGame.game),
            selectinload(Party.members).selectinload(PartyMember.player).selectinload(Player.region),
            selectinload(Party.members).selectinload(PartyMember.player).selectinload(Player.player_games).selectinload(PlayerGame.game),
        )
        .where(
            Party.game_id == game_id,
            Party.status == PartyStatus.OPEN,
        )
        .order_by(Party.created_at.desc())
        .limit(50)
    )

    result = await db.execute(q)
    candidates = result.scalars().all()

    scored: list[MatchResult] = []

    for party in candidates:
        # Skip full parties
        if len(party.members) >= party.max_size:
            continue

        # Skip if player already in this party
        if any(m.player_id == player.id for m in party.members):
            continue

        # Check skill range
        min_rank = SKILL_ORDER[party.min_skill]
        max_rank = SKILL_ORDER[party.max_skill]
        if not (min_rank <= player_skill_rank <= max_rank):
            continue

        # Compute avg skill of current members
        if party.members:
            avg_rank = sum(SKILL_ORDER[m.player.skill_level] for m in party.members) / len(party.members)
        else:
            avg_rank = 2  # default GOLD

        skill_distance = abs(player_skill_rank - avg_rank)
        if skill_distance > max_skill_distance:
            continue

        # Score computation
        region_score = _region_score(player, party)
        skill_score = max(0, int(100 - skill_distance * 20))
        fill_score = int((len(party.members) / party.max_size) * 30)
        availability_score = _availability_score(party)
        total = region_score + skill_score + fill_score + availability_score

        scored.append(MatchResult(
            party=party,
            match_score=total,
            region_score=region_score,
            skill_score=skill_score,
            fill_score=fill_score,
            availability_score=availability_score,
        ))

    scored.sort(key=lambda x: x.match_score, reverse=True)
    return scored[:limit]


def _region_score(player: Player, party: Party) -> int:
    if player.region_id and party.region_id == player.region_id:
        return 100
    # Neighboring check
    if player.region and party.region:
        player_code = player.region.code
        party_code = party.region.code
        if party_code in NEIGHBORING_REGIONS.get(player_code, set()):
            return 50
    return 0


def _availability_score(party: Party) -> int:
    if not party.members:
        return 0
    lfp_count = sum(
        1 for m in party.members
        if m.player.availability == AvailabilityStatus.LOOKING_FOR_PARTY
    )
    ratio = lfp_count / len(party.members)
    if ratio == 1.0:
        return 20
    elif ratio > 0:
        return 10
    return 0
