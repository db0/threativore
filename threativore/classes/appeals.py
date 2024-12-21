from typing import Any

import regex as re
from loguru import logger

import threativore.database as database
import threativore.exceptions as e
from threativore.enums import FilterAction, FilterType, UserRoleTypes, AppealStatus, EntityType
from threativore.flask import db
from threativore.orm.filters import Filter, FilterAppeal
from threativore.webhooks import webhook_parser

class ThreativoreAppeals:
    threativore = None
    
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
            logger.warning(f"{user_url} requested restoring of appeal {appeal_search.group(1)} but it doesn't seem to exist.")
            self.threativore.reply_to_pm(
                pm=pm,
                message=f"An Appeal with ID `{appeal_search.group(1)}` doesn't seem to exist."
            )
            return
        if filter_appeal.status == AppealStatus.RESTORED:
            logger.warning(f"{user_url} requested restoring of appeal {appeal_search.group(1)} but it had already been restored. Aborting.")
            self.threativore.reply_to_pm(
                pm=pm,
                message=(
                    f"You requested restoring appeal `{appeal_search.group(1)}` "
                    f"but it has already been restored by {filter_appeal.resolver.user_url}." 
                )
            )
            return
        if filter_appeal.status == AppealStatus.REJECTED:
            logger.warning(f"{user_url} requested restoring of previously rejected appeal {appeal_search.group(1)}. Will continue restoring.")
        for other_appeal in filter_appeal.filter_match.appeals:
            if other_appeal.id == filter_appeal.id:
                continue
            if other_appeal.status == AppealStatus.PENDING:
                other_appeal.status = AppealStatus.RESTORED
                self.threativore.reply_to_user_id(
                    user_id=other_appeal.creator_id,
                    message=(f"Someone else has succesfully appealed against action {filter_appeal.filter_match_id} and it has already been restored by our admin team."),
                    
                )                            
        filter_appeal.status = AppealStatus.RESTORED
        filter_appeal.resolver_id = user.id
        self.threativore.reply_to_user_id(
            user_id=filter_appeal.creator_id,
            message=(f"Your appeal against action {filter_appeal.filter_match_id} has been accepted and it has already been restored by our admin team."),
        )
        db.session.commit()
        if filter_appeal.filter_match.entity_type == EntityType.COMMENT:
            self.threativore.lemmy.comment.remove(
                comment_id=filter_appeal.filter_match.entity_id,
                removed=False,
                reason=f"Threativore automatic comment restoration from appeal: {filter_appeal.id}"
            )
        else:
            self.threativore.lemmy.post.remove(
                post_id=filter_appeal.filter_match.entity_id,
                removed=False,
                reason=f"Threativore automatic post restoration from appeal: {filter_appeal.id}"
            )
        self.threativore.reply_to_pm(
            pm=pm,
            message=f"You have successfully restored post {filter_appeal.filter_match.url} from appeal `{appeal_search.group(1)}`"
        )

    def parse_appeal_reject(self, appeal_search, pm):
        user_url = pm["creator"]["actor_id"].lower()
        user = database.get_user(user_url)
        if not user:
            raise e.ThreativoreException(f"{user_url} not known")
        if not user.has_role(UserRoleTypes.ADMIN) and not user.has_role(UserRoleTypes.MODERATOR):
            raise e.ThreativoreException(f"{user_url} doesn't have enough privileges to action appeals")
        reject_type = appeal_search.group(1).lower()
        filter_appeal = database.get_appeal(int(appeal_search.group(2)))
        if not filter_appeal:
            logger.warning(f"{user_url} requested {reject_type}ing of appeal {appeal_search.group(2)} but it doesn't seem to exist.")
            self.threativore.reply_to_pm(
                pm=pm,
                message=f"An Appeal with ID `{appeal_search.group(2)}` doesn't seem to exist."
            )
            return
        if filter_appeal.status != AppealStatus.PENDING:
            logger.warning(f"{user_url} requested {reject_type}ing of appeal {appeal_search.group(2)} but it had already been restored or rejected. Aborting.")
            self.threativore.reply_to_pm(
                pm=pm,
                message=(
                    f"You requested {reject_type}ing appeal `{appeal_search.group(2)}` "
                    f"but it has already been resolved by {filter_appeal.resolver.user_url}." 
                )
            )
            return
        filter_appeal.status = AppealStatus.REJECTED
        filter_appeal.resolver_id = user.id
        db.session.commit()
        if reject_type == 'reject':
            self.threativore.reply_to_user_id(
                user_id=filter_appeal.creator_id,
                message=(
                    f"Your appeal against against action {filter_appeal.filter_match_id} has been rejected "
                    f"with the following message:\n\n---\n\n{pm['private_message']['content']}."
                ),
            )
        self.threativore.reply_to_pm(
            pm=pm,
            message=f"You have successfully rejected appeal `{appeal_search.group(2)}`"
        )

    def parse_appeal_request(self, appeal_search, pm):
        creator_id = pm["creator"]["id"]
        creator_url = pm["creator"]["actor_id"]
        filter_match = database.get_filter_match(int(appeal_search.group(1)))
        if not filter_match:
            logger.warning(f"{creator_url} requested appeal restore of {appeal_search.group(1)} but it doesn't seem to exist.")
            return
        appeal = database.find_appeal_by_user(creator_id, filter_match.id)
        if appeal:
            if appeal.status != AppealStatus.PENDING:
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
                    message=(f"Someone else has succesfully appealed against action '{filter_match.id}' and it has already been restored by our admin team."),
                )
                return            
        new_appeal = FilterAppeal(
            pm_id = pm["private_message"]["id"],
            creator_id = creator_id,
            creator_url = creator_url.lower(),
            message = pm["private_message"]["content"],
            filter_match_id = filter_match.id,
            filter_id = filter_match.filter_id
            )
        db.session.add(new_appeal)
        db.session.commit()
        appeal_msg = (
            f"Threativore appeal has been lodged by {new_appeal.creator_url} "
            f"for action {new_appeal.filter_match_id} caused by regex `{filter_match.filter.regex}`.\n\n"
            f"reply with `threativore appeal restore {new_appeal.id}` to restore the item filtered, "
            f"reply with `threativore appeal reject {new_appeal.id}` to reject the appeal "
            "**and send your PM as the reason to the originating user**, "
            f"or reply with `threativore appeal ignore {new_appeal.id}` to simply mark the appeal as resolved.\n\n"
            f"The appeal message appears below:\n\n{quoted_appeal_message}\n\n"
            f"The filtered message appears below:\n\n{quoted_matched_content}"        
        )

        for admin in self.threativore.appeal_admins:
            quoted_appeal_message = '>' + new_appeal.message.replace('\n', '\n>')
            quoted_matched_content = '>' + filter_match.content.replace('\n', '\n>')
            admin.pm(content=appeal_msg)
        webhook_parser(appeal_msg)
        self.threativore.reply_to_pm(
            pm=pm,
            message=(
                f"Your appeal against threativore action `{filter_match.id}` has been lodged and will be reviewed by our admin team. "
                f"Your appeal ID is `{new_appeal.id}`."
            ),
        )
