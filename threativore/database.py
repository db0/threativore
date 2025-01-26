from datetime import datetime, timedelta
from threativore.enums import EntityType, FilterType, UserRoleTypes
from threativore.orm.filters import Filter, FilterMatch, FilterAppeal
from threativore.orm.seen import Seen
from threativore.orm.user import User, UserRole, UserTag
from threativore.orm.governance import GovernancePost, GovernancePostComment
from threativore.flask import db
from threativore.enums import GovernancePostType
from sqlalchemy.sql import exists
from sqlalchemy import func, or_, and_, not_


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

def find_appeal_by_user(creator_id: int, filter_match_id: int) -> FilterAppeal:
    return FilterAppeal.query.filter(
        FilterAppeal.filter_match_id == filter_match_id,
        FilterAppeal.creator_id == creator_id,
    ).first()

def get_appeal(appeal_id: int) -> FilterAppeal:
    return FilterAppeal.query.filter_by(id=appeal_id).first()

def get_user(user_url: str) -> User | None:
    return User.query.filter_by(user_url=user_url).first()

def get_user_from_override_email(user_email: str) -> User | None:
    return User.query.filter_by(email_override=user_email).first()

def actor_bypasses_filter(user_url: str) -> User:
    return db.session.query(
        exists().where(
            and_(
                UserRole.user_id == User.id,
                UserRole.user_role.in_([UserRoleTypes.ADMIN, UserRoleTypes.MODERATOR, UserRoleTypes.TRUSTED]),
            )
        ).where(
            User.user_url == user_url
        )
    ).scalar()


def has_been_seen(entity_id: int, entity_type: EntityType):
    return (
        Seen.query.filter_by(
            entity_id=entity_id,
            entity_type=entity_type,
        ).count()
        == 1
    )

def has_any_entry_been_seen(entity_ids: list[int], entity_type: EntityType) -> bool:
    return (
        Seen.query.filter(
            Seen.entity_id.in_(entity_ids),
            Seen.entity_type == entity_type,
        ).count()
        >= 1
    )

def filter_match_exists(entity_id: int) -> bool:
    return FilterMatch.query.filter_by(entity_id=entity_id).count() == 1

def get_filter_match_by_entity(entity_id: int) -> FilterMatch | None:
    return FilterMatch.query.filter_by(entity_id=entity_id).first()

def get_filter_match(filter_match_id: int) -> FilterMatch | None:
    return FilterMatch.query.filter_by(id=filter_match_id).first()

def delete_seen_rows(days_older_than:int=7):
    return Seen.query.filter(
        Seen.updated < datetime.utcnow() - timedelta(days=days_older_than)
    ).delete()


def count_user_vouches(user_id: int):
    return UserTag.query.join(User).filter(
        UserTag.tag == "vouched",
        User.id == user_id
    ).count()

def get_tag(tag: str, user_id: int):
    return UserTag.query.join(User).filter(
        UserTag.tag == tag,
        User.id == user_id,
    ).first()

def get_governance_post(post_id: int) -> GovernancePost | None:
    return GovernancePost.query.filter(
        GovernancePost.post_id == post_id,
    ).first()

def get_all_active_governance_posts() -> list[GovernancePost]:
    return GovernancePost.query.filter(
        or_(
            GovernancePost.expires == None,
            # We give some buffer to be able to do final updates
            GovernancePost.expires > datetime.utcnow() - timedelta(hours=1)
        )
    ).all()

def replied_to_gpost_comment(parent_id):
    return (
        GovernancePostComment.query.filter(
            GovernancePostComment.replied.is_(True),
            GovernancePostComment.parent_id == parent_id,
        ).count()
        >= 1
    )


def get_comment_flair_reply(parent_id):
    return (
        GovernancePostComment.query.filter(
            GovernancePostComment.replied.is_(True),
            GovernancePostComment.parent_id == parent_id,
        ).first()
    )

def get_gpost(gpost_id: int):
    return GovernancePost.query.filter_by(post_id=gpost_id).first()

def get_open_votes():
    return GovernancePost.query.filter(
        GovernancePost.expires > datetime.utcnow(),
        GovernancePost.post_type == GovernancePostType.SIMPLE_MAJORITY,
    ).all()