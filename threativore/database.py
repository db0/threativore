from threativore.enums import EntityType, FilterType
from threativore.orm.filters import Filter, FilterMatch
from threativore.orm.seen import Seen
from threativore.orm.user import User


def get_all_filters(filter_type: FilterType, regex_search: str | None = None) -> list[Filter]:
    query = Filter.query.filter_by(
        filter_type=filter_type,
    )
    if regex_search:
        query = query.filter(
            Filter.regex.like(f"%{regex_search}%"),
        )
    return query.all()


def does_filter_exist(filter_regex: str) -> bool:
    return Filter.query.filter_by(regex=filter_regex).count() == 1


def get_filter(filter_regex: str) -> Filter:
    return Filter.query.filter_by(regex=filter_regex).first()


def get_user(user_url: str) -> User:
    return User.query.filter_by(user_url=user_url).first()


def has_been_seen(entity_id: int, entity_type: EntityType):
    return (
        Seen.query.filter_by(
            entity_id=entity_id,
            entity_type=entity_type,
        ).count()
        == 1
    )

def has_any_entry_been_seen(entity_ids: list[int], entity_type: EntityType):
    return (
        Seen.query.filter(
            Seen.entity_id.in_(entity_ids),
            Seen.entity_type == entity_type,
        ).count()
        >= 1
    )

def filter_match_exists(entity_id: int) -> bool:
    return FilterMatch.query.filter_by(entity_id=entity_id).count() == 1