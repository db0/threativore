from typing import Any

import regex as re
from loguru import logger

import threagetarian.database as database
import threagetarian.exceptions as e
from threagetarian.enums import FilterAction, FilterType, UserRoleTypes
from threagetarian.flask import db
from threagetarian.orm.filters import Filter


class ThreagetarianFilters:
    def __init__(self, threagetarian):
        self.threagetarian = threagetarian

    def add_filter(
        self,
        filter: str,
        user_url: str,
        reason: str,
        filter_action: FilterAction,
        filter_type: FilterType,
        description: str | Any = None,
    ):
        user = database.get_user(user_url)
        if not user:
            raise e.ThreagetarianException(f"{user_url} not known")
        if not user.has_role(UserRoleTypes.ADMIN) and not user.has_role(UserRoleTypes.MODERATOR):
            raise e.ThreagetarianException(f"{user_url} doesn't have enough privileges to add filters")
        existing_filter = database.get_filter(filter)
        if existing_filter:
            raise e.ReplyException(f"Filter already exists: {existing_filter.regex} - {existing_filter.filter_type}")
        new_filter = Filter(
            regex=filter,
            user_id=user.id,
            description=description,
            reason=reason,
            filter_action=filter_action,
            filter_type=filter_type,
        )
        db.session.add(new_filter)
        db.session.commit()
        logger.info(f"{user_url} just added {filter_type.name.lower()} filter '{filter}' with action {filter_action.name}")

    def remove_filter(self, filter: str, user_url: str):
        user = database.get_user(user_url)
        if not user:
            raise e.ThreagetarianException(f"{user_url} not known")
        if not user.has_role(UserRoleTypes.ADMIN) and not user.has_role(UserRoleTypes.MODERATOR):
            raise e.ThreagetarianException(f"{user_url} doesn't have enough privileges to remove filters")
        existing_filter = database.get_filter(filter)
        if not existing_filter:
            return
        db.session.delete(existing_filter)
        db.session.commit()

    def modify_filter(
        self,
        existing_filter_regex: str,
        user_url: str,
        new_filter_regex: str | None = None,
        reason: str | None = None,
        filter_action: FilterAction | None = None,
        filter_type: FilterType | None = None,
        description: str | None = None,
    ) -> Filter:
        user = database.get_user(user_url)
        if not user:
            raise e.ThreagetarianException(f"{user_url} not known")
        if not user.can_do_filters():
            raise e.ThreagetarianException(f"{user_url} doesn't have enough privileges to modify filters")
        existing_filter = database.get_filter(existing_filter_regex)
        if not existing_filter:
            raise e.ReplyException(f"filter {existing_filter_regex} does not exist.")
        if new_filter_regex is not None:
            existing_filter.regex = new_filter_regex
        if reason is not None:
            existing_filter.reason = reason
        if filter_action is not None:
            existing_filter.filter_action = filter_action
        if filter_type is not None:
            existing_filter.filter_type = filter_type
        if description is not None:
            existing_filter.description = description
        db.session.commit()
        return existing_filter

    def print_all_filters(self):
        logger.info([(f.regex, f.reason) for f in database.get_all_filters(FilterType.COMMENT)])
        logger.info([(f.regex, f.reason) for f in database.get_all_filters(FilterType.REPORT)])

    def parse_filter_pm(self, filter_search, pm):
        user_url = pm["creator"]["actor_id"].lower()
        requesting_user = database.get_user(user_url)
        if not requesting_user:
            logger.debug(user_url)
            raise e.ReplyException("Sorry, you do not have enough rights to do a filtering operation.")
        if not requesting_user.can_do_filters():
            logger.debug(requesting_user.roles)
            raise e.ReplyException("Sorry, you do not have enough rights to do a filtering operation.")
        # logger.info(pm['private_message']['content'])
        filter_type = FilterType[filter_search.group(2).upper()]
        filter_regex = filter_search.group(3).strip()
        filter_method = filter_search.group(1).lower()
        if filter_method in ["add", "modify"]:
            filter_reason_search = re.search(r"reason: ?`(.+?)`[ \n]*?", pm["private_message"]["content"], re.IGNORECASE)
            filter_description_search = re.search(r"description: ?`(.+?)`[ \n]*?", pm["private_message"]["content"], re.IGNORECASE)
            filter_description = None
            if filter_description_search:
                filter_description = filter_description_search.group(1).strip()
            fa_values = "|".join([e.name for e in FilterAction])
            filter_action_search = re.search(rf"action: ?({fa_values})", pm["private_message"]["content"], re.IGNORECASE)
            filter_action = None
            if filter_action_search:
                filter_action = FilterAction[filter_action_search.group(1).upper()]
            if filter_method == "add":
                if not filter_reason_search:
                    raise e.ReplyException("New filter needs reason")
                filter_reason = filter_reason_search.group(1).strip()
                if filter_action is None:
                    filter_action = FilterAction.REMOVE
                # logger.info([filter_type,filter_regex,filter_reason,filter_description,filter_action])
                self.add_filter(
                    filter=filter_regex,
                    user_url=user_url,
                    reason=filter_reason,
                    filter_action=filter_action,
                    filter_type=filter_type,
                    description=filter_description,
                )
                self.threagetarian.reply_to_pm(
                    pm=pm,
                    message=(
                        f"New Filter has been succesfully added:\n\n\n"
                        "---\n"
                        f"* regex: `{filter_regex}`\n"
                        f"* reason: {filter_reason}\n"
                        f"* filter_action: {filter_action.name}\n"
                        f"* filter_type: {filter_type.name}\n"
                        f"* description: {filter_description}"
                    ),
                )
            if filter_method == "modify":
                mew_filter_search = re.search(r"new[ _]filter: ?`(.+?)`[ \n]*?", pm["private_message"]["content"], re.IGNORECASE)
                mew_filter = None
                if mew_filter_search:
                    mew_filter = mew_filter_search.group(1).strip()
                filter_reason = None
                if filter_reason_search:
                    filter_reason = filter_reason_search.group(1).strip()
                modified_filter = self.modify_filter(
                    existing_filter_regex=filter_regex,
                    new_filter_regex=mew_filter,
                    user_url=user_url,
                    reason=filter_reason,
                    filter_action=filter_action,
                    filter_type=filter_type,
                    description=filter_description,
                )
                self.threagetarian.reply_to_pm(
                    pm=pm,
                    message=(
                        f"Filter has been succesfully modified:\n\n\n"
                        "---\n"
                        f"* regex: `{modified_filter.regex}`\n"
                        f"* reason: {modified_filter.reason}\n"
                        f"* filter_action: {modified_filter.filter_action.name}\n"
                        f"* filter_type: {modified_filter.filter_type.name}\n"
                        f"* description: {modified_filter.description}"
                    ),
                )
        if filter_method == "remove":
            self.remove_filter(filter=filter_regex)
            self.threagetarian.reply_to_pm(
                pm=pm,
                message=(f"Filter has been succesfully remmoved:\n\n\n" "---\n" f"* regex: `{filter_regex}`"),
            )
        if filter_method == "show":
            filtered_filters = [(f) for f in database.get_all_filters(FilterType.COMMENT, filter_regex)]
            filters_string = ""
            for ffilter in filtered_filters:
                filters_string += (
                    "\n\n---\n"
                    f"* regex: `{ffilter.regex}`\n"
                    f"* reason: {ffilter.reason}\n"
                    f"* filter_action: {ffilter.filter_action.name}\n"
                    f"* description: {ffilter.description}"
                )

            self.threagetarian.reply_to_pm(
                pm=pm,
                message=(f"Here are all the available {filter_type.name} filters containing `{filter_regex}`:\n\n\n{filters_string}"),
            )

    def parse_filter_list_pm(self, filter_search, pm):
        requesting_user = database.get_user(pm["creator"]["actor_id"])
        if not requesting_user:
            raise e.ReplyException("Sorry, you do not have enough rights to do a filtering operation.")
        if not requesting_user.can_do_filters():
            raise e.ReplyException("Sorry, you do not have enough rights to do a filtering operation.")
        # logger.info(pm['private_message']['content'])
        filter_type = FilterType[filter_search.group(1).upper()]
        all_filters = [(f.regex) for f in database.get_all_filters(FilterType.COMMENT)]
        if len(all_filters) == 0:
            self.threagetarian.reply_to_pm(pm=pm, message=f"There are currently no {filter_type.name} defined.")
            return
        joined_filters = "`\n* `".join(all_filters)
        self.threagetarian.reply_to_pm(
            pm=pm,
            message=(f"Here are all the available {filter_type.name} filter regexp:\n\n\n" "---\n" f"* `{joined_filters}`"),
        )
