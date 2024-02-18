from threagetarian.enums import EntityType, FilterType
from threagetarian.orm.filters import Filter
from threagetarian.orm.seen import Seen
from threagetarian.orm.user import User


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
