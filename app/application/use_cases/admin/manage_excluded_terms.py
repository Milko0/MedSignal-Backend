"""FR-26: manage non-specific reaction terms excluded from signals and label gaps."""
from app.application.dtos.admin import ExcludedTermDto
from app.application.ports.excluded_term_repository import ExcludedTermRepository
from app.domain.entities.excluded_term import ExcludedTerm
from app.domain.exceptions import NotFoundError
from app.domain.value_objects.reaction_term import normalize_reaction


class ManageExcludedTerms:
    def __init__(self, terms: ExcludedTermRepository, clock) -> None:
        self.terms, self.clock = terms, clock

    async def list(self) -> list[ExcludedTermDto]:
        return [ExcludedTermDto(term=t.term) for t in sorted(await self.terms.list(), key=lambda t: t.term)]

    async def add(self, term: str) -> ExcludedTermDto:
        norm = normalize_reaction(term)
        await self.terms.add(ExcludedTerm(term=norm, added_at=self.clock.now()))
        return ExcludedTermDto(term=norm)

    async def remove(self, term: str) -> None:
        if not await self.terms.remove(normalize_reaction(term)):
            raise NotFoundError("Term not found")
