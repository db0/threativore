from typing import Any

import regex as re
from loguru import logger

import threativore.database as database
import threativore.exceptions as e
from threativore.enums import FilterAction, FilterType, UserRoleTypes, AppealStatus, EntityType
from threativore.flask import db
from threativore.orm.filters import Filter, FilterAppeal
from threativore.threativore import Threativore

class ThreativoreAppeals:
    threativore: "Threativore" = None
    
    def __init__(self, threativore):
        self.threativore = threativore

    def parse_appeal_restore(self, appeal_search, pm):
        user_url = pm["creator"]["actor_id"].lower()
        user = database.get_user(user_url)
        if not user:
            raise e.ThreativoreException(f"{user_url} not known")
        if not user.has_role(UserRoleTypes.ADMIN) and not user.has_role(UserRoleTypes.MODERATOR):
            raise e.ThreativoreException(f"{user_url} doesn't have enough privileges to action appeals")
        filter_appeal = database.get_appeal(int(appeal_search.group(1)))
        if not filter_appeal:
            logger.warning(f"{pm["private_message"]["actor_id"]} requested restoring of appeal {appeal_search.group(1)} but it doesn't seem to exist.")
            return
        if filter_appeal.status == AppealStatus.RESTORED:
            logger.warning(f"{pm["private_message"]["actor_id"]} requested restoring of appeal {appeal_search.group(1)} but it had already been restored. Aborting.")
            return
        if filter_appeal.status == AppealStatus.REJECTED:
            logger.warning(f"{pm["private_message"]["actor_id"]} requested restoring of previously ignored appeal {appeal_search.group(1)}. Will continue restoring.")
        for other_appeal in filter_appeal.filter_match.appeals:
            if other_appeal.id == filter_appeal.id:
                continue
            if other_appeal.status == AppealStatus.PENDING:
                other_appeal.status = AppealStatus.RESTORED
                self.threativore.reply_to_user_id(
                    pm=other_appeal.creator_id,
                    message=(f"Your appeal against action {filter_appeal.filter_match_id} has been accepted and it has already been restored by our admin team."),
                )                            
        filter_appeal.status = AppealStatus.RESTORED
        self.threativore.reply_to_user_id(
            pm=filter_appeal.creator_id,
            message=(f"Someone else has succesfully appealed against action {filter_appeal.filter_match_id} and it has already been restored by our admin team."),
        )
        db.session.commit()
        if filter_appeal.filter_match.entity_type == EntityType.COMMENT:
            self.lemmy.comment.remove(
                comment_id=filter_appeal.filter_match.entity_id,
                removed=False,
                reason=f"Threativore automatic comment restoration from appeal: {filter_appeal.id}"
            )
        else:
            self.lemmy.post.remove(
                post_id=filter_appeal.filter_match.entity_id,
                removed=False,
                reason=f"Threativore automatic post restoration from appeal: {filter_appeal.id}"
            )


    def parse_appeal_reject(self, appeal_search, pm):
        user_url = pm["creator"]["actor_id"].lower()
        user = database.get_user(user_url)
        if not user:
            raise e.ThreativoreException(f"{user_url} not known")
        if not user.has_role(UserRoleTypes.ADMIN) and not user.has_role(UserRoleTypes.MODERATOR):
            raise e.ThreativoreException(f"{user_url} doesn't have enough privileges to action appeals")
        reject_type = database.get_appeal(int(appeal_search.group(1)))
        filter_appeal = database.get_appeal(int(appeal_search.group(2)))
        if not filter_appeal:
            logger.warning(f"{pm["private_message"]["actor_id"]} requested {reject_type}ing of appeal {appeal_search.group(1)} but it doesn't seem to exist.")
            return
        if filter_appeal.status != AppealStatus.PENDING:
            logger.warning(f"{pm["private_message"]["actor_id"]} requested {reject_type}ing of appeal {appeal_search.group(1)} but it had already been restored or rejected. Aborting.")
            return
        filter_appeal.status = AppealStatus.REJECTED
        db.session.commit()
        if reject_type == 'reject':
            self.threativore.reply_to_user_id(
                pm=filter_appeal.creator_id,
                message=(
                    f"Your appeal against against action {filter_appeal.filter_match_id} has been rejected "
                    f"with the following message:\n\n---{pm["private_message"]["content"]}."
                ),
            )

    def parse_appeal_request(self, appeal_search, pm):
        filter_match = database.get_filter_match(int(appeal_search.group(1)))
        if not filter_match:
            logger.warning(f"{pm["private_message"]["actor_id"]} requested appeal restore of {appeal_search.group(1)} but it doesn't seem to exist.")
            return
        creator_id = pm["private_message"]["creator_id"]
        appeal = database.find_appeal_by_user(creator_id, filter_match.id)
        if appeal:
            if appeal.resolved:
                self.threativore.reply_to_pm(
                    pm=pm,
                    message=(f"You have already appealed against threativore action {filter_match.id} and it has already been resolved by our admin team."),
                )
            else:
                self.threativore.reply_to_pm(
                    pm=pm,
                    message=(f"You have already appealed against threativore action {filter_match.id} and it is waiting for resolution by our admin team. Please be patient."),
                )
            return
        for appeal in filter_match.appeals:
            if appeal.status == AppealStatus.RESTORED:
                self.threativore.reply_to_pm(
                    pm=pm,
                    message=(f"Someone else has succesfully appealed against action {filter_match.id} and it has already been restored by our admin team."),
                )
                return            
        new_appeal = FilterAppeal(
            pm_id = pm["private_message"]["id"],
            creator_id = creator_id,
            creator_url = pm["private_message"]["actor_id"].lower(),
            message = pm["private_message"]["content"],
            filter_match_id = filter_match.id,
            filter_id = filter_match.filter_id
            )
        db.session.add(new_appeal)
        db.session.commit()
        for admin in self.threativore.appeal_admins:
            admin.pm(
                message=(
                    f"Threativore appeal has been lodged by {new_appeal.creator_url} for action {new_appeal.filter_match_id} caused by regex {filter_match.filter.regex}.\n\n",
                    f"reply with `threativore appeal restore {new_appeal.id}` to restore the item filtered, "
                    f"reply with `threativore appeal reject {new_appeal.id}` to reject the appeal **and send your PM as the reason to the originating user**, "
                    f"or reply with `threativore appeal ignore {new_appeal.id}` to simply mark the appeal as resolved.\n\n"
                    "The appeal message appears below:\n\n---",
                    new_appeal.message,
                    "The filtered message appears below:\n\n---",
                    filter_match.content,
                )
            )
