from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any

import regex as re
from loguru import logger

import threativore.database as database
import threativore.exceptions as e
from threativore.classes.filters import ThreativoreFilters
from threativore.classes.appeals import ThreativoreAppeals
from threativore.classes.users import ThreativoreUsers
from threativore.enums import EntityType, FilterAction, FilterType, UserRoleTypes
from threativore.flask import APP, db
from threativore.orm.filters import FilterMatch, FilterAppeal
from threativore.orm.seen import Seen
from threativore.orm.user import User
from pythorhead.types.sort import CommentSortType
from threativore.argparser import args
from threativore.config import Config

from threativore.webhooks import webhook_parser

class Threativore:

    appeal_admins: list = []    

    def __init__(self, _base_lemmy):
        self.lemmy = _base_lemmy.lemmy
        self.filters = ThreativoreFilters(self)
        self.users = ThreativoreUsers(self)
        self.appeals = ThreativoreAppeals(self)
        self.ensure_admin_exists()
        self.prepare_appeal_objects()

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        pass

    @logger.catch(reraise=True)
    def ensure_admin_exists(self):
        with APP.app_context():
            admin_user_url = Config.threativore_admin_url.lower()
            if not admin_user_url:
                raise e.ThreativoreException("THREATIVORE_ADMIN_URL env not set")
            admin = database.get_user(admin_user_url)
            if not admin:
                admin = User(user_url=admin_user_url)
                db.session.add(admin)
                db.session.commit()
            admin.add_role(UserRoleTypes.ADMIN)

    def prepare_appeal_objects(self):
        for admin_username in Config.threativore_appeal_urls:
            admin_account = self.lemmy.get_user(username=admin_username)
            if admin_account is None:
                logger.warning(f"Cannot discover appeal admin account {admin_username}.")
                continue
            self.appeal_admins.append(admin_account)

    def resolve_reports(self):
        logger.debug("Checking Reports...")
        self.resolve_reports()

    def resolve_reports(self):
        rl = self.lemmy.comment.report_list(unresolved_only=False, limit=5)
        for report in self.lemmy.post.report_list():
            rl.append(report)
        # logger.info(json.dumps(rl, indent=4))
        comment_filters = database.get_all_filters(FilterType.COMMENT)
        report_filters = database.get_all_filters(FilterType.REPORT)
        username_filters = database.get_all_filters(FilterType.USERNAME)
        sorted_filters = sorted(report_filters + comment_filters + username_filters, key=lambda x: x.filter_action.value)
        for report in rl:
            if "comment_report" in report.keys():
                item_type = "comment"
                target_type_enum = EntityType.COMMENT
            else:
                item_type = "post"
                target_type_enum = EntityType.POST
            entity_removed = False
            entity_banned = False
            report_id: int = report[f"{item_type}_report"]["id"]
            if database.has_been_seen(report_id, EntityType.REPORT):
                continue
            for tfilter in sorted_filters:
                if entity_removed:
                    break
                matching_string = ""
                matching_content = ""
                if tfilter.filter_type in [FilterType.REPORT,FilterType.COMMENT]:
                    actor_id = report[f'{item_type}_creator']['actor_id']
                    if item_type == "comment":
                        filter_match = re.search(tfilter.regex, report[f"{item_type}"]["content"], re.IGNORECASE)
                        matching_string = f'{item_type} content: {report[f"{item_type}"]["content"]}'
                        matching_content = report[f"{item_type}"]["content"]
                    elif item_type == "post":
                        filter_match = re.search(tfilter.regex, report[f"{item_type}"]["name"], re.IGNORECASE)
                        matching_string = f'{item_type} name: {report[f"{item_type}"]["name"]}'
                        matching_content = report[f"{item_type}"]["name"]
                    elif "body" in report[f"{item_type}"]:
                        filter_match = re.search(tfilter.regex, report[f"{item_type}"]["body"], re.IGNORECASE)
                        matching_string = f'{item_type} body: {report[f"{item_type}"]["body"]}'
                        matching_content = report[f"{item_type}"]["body"]
                if tfilter.filter_type == FilterType.USERNAME:
                    filter_match = re.search(tfilter.regex, report["creator"]["name"], re.IGNORECASE)
                    matching_string = f'{item_type} username: {report["creator"]["name"]}'
                    matching_content = report["creator"]["name"]
                if filter_match:
                    logger.info(f"Matched anti-spam filter from {actor_id} for reported {matching_string[0:50]}... " f"regex: {filter_match}")
                    webhook_parser(f"Matched anti-spam filter from {actor_id} for reported {matching_string[0:50]}... " f"regex: {filter_match}")
                    if tfilter.filter_action != FilterAction.REPORT:
                        if not database.filter_match_exists(report[f"{item_type}"]["id"]):
                            new_match = FilterMatch(
                                actor_id=report[f"{item_type}_creator"]["actor_id"],
                                entity_id=report[f"{item_type}"]["id"],
                                entity_type=target_type_enum,
                                report_id=report_id,
                                url=report[f"{item_type}"]["ap_id"],
                                content=matching_content,
                                filter_id=tfilter.id,
                            )
                            db.session.add(new_match)
                            db.session.commit()
                        # logger.warning("Would remove comment from report")
                        if item_type == "comment":
                            self.lemmy.comment.remove(
                                comment_id=report["comment"]["id"],
                                removed=True,
                                reason=(
                                    f"Threativore automatic comment removal from report: {tfilter.reason}",
                                    f"Appeal by sending a PM with your reasoning and including the text: `threativore request appeal {new_match.id}`",
                                ),
                            )
                        else:
                            self.lemmy.post.remove(
                                post_id=report["post"]["id"],
                                removed=True,
                                reason=(
                                    f"Threativore automatic post removal from report: {tfilter.reason}",
                                    f"Appeal by sending a PM with your reasoning and including the text: `threativore request appeal {new_match.id}`",
                                ),
                            )
                        entity_removed = True
                        if not entity_banned and tfilter.filter_action in [FilterAction.PERMABAN,FilterAction.REMBAN,FilterAction.BAN30,FilterAction.BAN7]:
                            expires = None
                            if tfilter.filter_action == FilterAction.BAN30:
                                expires = datetime.utcnow() + timedelta(days=30)
                            if tfilter.filter_action == FilterAction.BAN7:
                                expires = datetime.utcnow() + timedelta(days=7)
                            remove_all=False
                            if tfilter.filter_action == FilterAction.REMBAN:
                                remove_all=True
                            logger.info(f"Banned {report[f'{item_type}_creator']['actor_id']} for {tfilter.filter_action.name}")
                            webhook_parser(f"Banned {report[f'{item_type}_creator']['actor_id']} for {tfilter.filter_action.name}")
                            self.lemmy.user.ban(
                                ban=True,
                                expires=expires,
                                person_id=report[f"{item_type}_creator"]["id"],
                                reason=(
                                    f"Threativore automatic ban from {item_type} report: {tfilter.reason}.\n\n",
                                    f"Appeal by sending PM with your reasoning and including the text: `threativore request appeal {new_match.id}`",
                                ),
                                remove_data=remove_all,
                            )
                            entity_banned = True
            seen_report = Seen(
                entity_id=report_id,
                entity_type=EntityType.REPORT,
                entity_url=report[item_type]["ap_id"],
            )
            db.session.add(seen_report)
            db.session.commit()

    def check_comments(self):
        seen_page_previously = False
        page = 1
        all_ids_checked_this_run = []
        while not seen_page_previously and page <= 10:
            seen_page_previously, ids_checked = self.check_comments_page(page, all_ids_checked_this_run)
            page += 1
            all_ids_checked_this_run += ids_checked
        

    def check_comments_page(self, page:int=1, ids_checked_already: list[int] = []):
        logger.debug(f"Checking Comments page {page}...")
        cm = self.lemmy.comment.list(limit=50,sort=CommentSortType.New, page=page)
        all_ids = [comment["comment"]["id"] for comment in cm if comment["comment"]["id"] not in ids_checked_already]
        seen_any_previously = database.has_any_entry_been_seen(all_ids, EntityType.COMMENT)
        # logger.debug([seen_any_previously, len(all_ids)])
        # logger.info(json.dumps(cm, indent=4))
        comment_filters = database.get_all_filters(FilterType.COMMENT)
        username_filters = database.get_all_filters(FilterType.USERNAME)
        sorted_filters = sorted(comment_filters + username_filters, key=lambda x: x.filter_action.value)
        for comment in cm:
            entity_removed = False
            entity_reported = False
            entity_banned = False
            comment_id: int = comment["comment"]["id"]
            if comment['creator']['actor_id'] == "https://lemmy.dbzer0.com/u/Flatworm7591":
                logger.debug(comment["comment"]["content"])
            if database.has_been_seen(comment_id, EntityType.COMMENT):
                continue
            user_url = comment["creator"]["actor_id"]
            if database.actor_bypasses_filter(user_url):
                logger.debug(f"Bypassing checks on user {user_url}")
                continue
            for tfilter in sorted_filters:
                matching_string = ""
                matching_content = ""
                if entity_removed:
                    break
                if entity_reported and tfilter.filter_action == FilterAction.REPORT:
                    continue
                if tfilter.filter_type == FilterType.COMMENT:
                    filter_match = re.search(tfilter.regex, comment["comment"]["content"], re.IGNORECASE)
                    matching_string = f'comment body: {comment["comment"]["content"]}'
                    matching_content = comment["comment"]["content"]
                if tfilter.filter_type == FilterType.USERNAME:
                    filter_match = re.search(tfilter.regex, comment["creator"]["name"], re.IGNORECASE)
                    matching_string = f'commenter username: {comment["creator"]["name"]}'
                    matching_content = comment["creator"]["name"]
                # logger.info([comment["comment"]["content"], f.regex])
                if filter_match:
                    logger.info(f"Matched anti-spam filter from {user_url} for {matching_string[0:50]}... " f"regex: {filter_match}")
                    webhook_parser(f"Matched anti-spam filter from {user_url} for {matching_string[0:50]}... " f"regex: {filter_match}")
                    # Comments
                    if not database.filter_match_exists(comment_id):
                        new_match = FilterMatch(
                            actor_id=user_url,
                            entity_id=comment_id,
                            entity_type=EntityType.COMMENT,
                            url=comment["comment"]["ap_id"],
                            content=matching_content,
                            filter_id=tfilter.id,
                        )
                        db.session.add(new_match)
                        db.session.commit()
                    if tfilter.filter_action == FilterAction.REPORT:
                        self.lemmy.comment.report(
                            comment_id=comment_id,
                            reason=f"Threativore automatic comment report: {tfilter.reason}"
                        )
                        entity_reported = True
                    else:
                        # BETA TESTING ONLY
                        # logger.warning("Would remove comment")
                        # logger.debug(f"Reported {comment_id}")
                        # self.lemmy.comment.report(
                        #     comment_id=comment_id,
                        #     reason=f"Threativore automatic beta testing report: {tfilter.reason}",
                        # )
                        # entity_reported = True

                        self.lemmy.comment.remove(
                            comment_id=comment_id,
                            removed=True,
                            reason=(
                                f"Threativore automatic comment removal: {tfilter.reason}",
                                f"Appeal by sending PM with your reasoning and including the text: `threativore request appeal {new_match.id}`",
                            ),
                        )
                        entity_removed = True
                        if not entity_banned and tfilter.filter_action in [FilterAction.PERMABAN,FilterAction.REMBAN,FilterAction.BAN30,FilterAction.BAN7]:
                            expires = None
                            if tfilter.filter_action == FilterAction.BAN30:
                                expires = datetime.utcnow() + timedelta(days=30)
                            if tfilter.filter_action == FilterAction.BAN7:
                                expires = datetime.utcnow() + timedelta(days=7)
                            remove_all=False
                            if tfilter.filter_action == FilterAction.REMBAN:
                                remove_all=True
                            logger.info(f"Banned {user_url} for {tfilter.filter_action.name}")
                            webhook_parser(f"Banned {user_url} for {tfilter.filter_action.name}")
                            self.lemmy.user.ban(
                                ban=True,
                                expires=expires,
                                person_id=comment["creator"]["id"],
                                reason=(
                                    f"Threativore automatic ban from comment: {tfilter.reason}",
                                    f"Appeal by sending PM with your reasoning and including the text: `threativore request appeal {new_match.id}`",
                                ),
                                remove_data=remove_all,
                            )
                            entity_banned = True
            seen_comment = Seen(
                entity_id=comment_id,
                entity_type=EntityType.COMMENT,
                entity_url=comment["comment"]["ap_id"],
            )
            db.session.add(seen_comment)
            db.session.commit()
        return (seen_any_previously,all_ids)


    def check_posts(self):
        seen_page_previously = False
        page = 1
        all_ids_checked_this_run = []
        while not seen_page_previously and page <= 10:
            seen_page_previously, ids_checked = self.check_posts_page(page, all_ids_checked_this_run)
            page += 1
            all_ids_checked_this_run += ids_checked

    def check_posts_page(self, page:int=1, ids_checked_already: list[int] = []):
        logger.debug(f"Checking Posts page {page}...")
        cm = self.lemmy.post.list(limit=10,sort=CommentSortType.New, page=page)
        all_ids = [post["post"]["id"] for post in cm if post["post"]["id"] not in ids_checked_already]
        seen_any_previously = database.has_any_entry_been_seen(all_ids, EntityType.POST)
        # logger.debug([seen_any_previously, len(all_ids)])
        # logger.info(json.dumps(cm, indent=4))
        comment_filters = database.get_all_filters(FilterType.COMMENT)
        url_filters = database.get_all_filters(FilterType.URL)
        username_filters = database.get_all_filters(FilterType.USERNAME)
        sorted_filters = sorted(comment_filters + username_filters + url_filters, key=lambda x: x.filter_action.value)
        for post in cm:
            post_id: int = post["post"]["id"]
            if database.has_been_seen(post_id, EntityType.POST):
                continue
            user_url = post["creator"]["actor_id"]
            if database.actor_bypasses_filter(user_url):
                logger.debug(f"Bypassing checks on user {user_url}")
                continue
            entity_removed = False
            entity_reported = False
            entity_banned = False
            for tfilter in sorted_filters:
                matching_string = ""
                matching_content = ""
                if entity_removed:
                    break
                if entity_reported and tfilter.filter_action == FilterAction.REPORT:
                    continue
                matched_filter = False
                if tfilter.filter_type == FilterType.COMMENT:
                    filter_match = re.search(tfilter.regex, post["post"]["name"], re.IGNORECASE)
                    if filter_match:
                        matched_filter = True
                        matching_string = f'post title: {post["post"]["name"]}'
                        matching_content = post["post"]["name"]
                    elif "body" in post["post"]:
                        filter_match = re.search(tfilter.regex, post["post"]["body"], re.IGNORECASE)
                        if filter_match:
                            matched_filter = True
                            matching_string = f'post body: {post["post"]["body"]}'
                            matching_content = post["post"]["body"]
                if "url" in post["post"] and tfilter.filter_type == FilterType.URL:
                    filter_match = re.search(tfilter.regex, post["post"]["url"], re.IGNORECASE)
                    if filter_match:
                        matched_filter = True
                        matching_string = f'post url: {post["post"]["url"]}'
                        matching_content = post["post"]["url"]
                if tfilter.filter_type == FilterType.USERNAME:
                    filter_match = re.search(tfilter.regex, post["creator"]["name"], re.IGNORECASE)
                    if filter_match:
                        matched_filter = True
                        matching_string = f'poster username: {post["creator"]["name"]}'
                        matching_content = post["creator"]["name"]
                # logger.info([comment["comment"]["content"], f.regex])
                if matched_filter:
                    logger.info(f"Matched anti-spam filter from {user_url} for {matching_string[0:50]}... " f"regex: {filter_match}")
                    webhook_parser(f"Matched anti-spam filter from {user_url} for {matching_string[0:50]}... " f"regex: {filter_match}")
                    if not database.filter_match_exists(post_id):
                        new_match = FilterMatch(
                            actor_id=user_url,
                            entity_id=post_id,
                            entity_type=EntityType.POST,
                            url=post["post"]["ap_id"],
                            content=matching_content,
                            filter_id=tfilter.id,
                        )
                        db.session.add(new_match)
                        db.session.commit()
                    if tfilter.filter_action == FilterAction.REPORT:
                        self.lemmy.post.report(
                            post_id=post_id,
                            reason=f"Threativore automatic post report: {tfilter.reason}",
                        )
                        entity_reported = True
                    else:
                        # BETA TESTING ONLY
                        # logger.warning("Would remove post")
                        # self.lemmy.post.report(
                        #     post_id=post_id,
                        #     reason=f"Threativore automatic beta testing report: {tfilter.reason}",
                        # )
                        entity_reported = True
                        self.lemmy.post.remove(
                            post_id=post_id,
                            removed=True,
                            reason=(
                                f"Threativore automatic post removal: {tfilter.reason}",
                                f"Appeal by sending PM with your reasoning and including the text: `threativore request appeal {new_match.id}`",
                            ),
                        )
                        entity_removed = True
                        if not entity_banned and tfilter.filter_action in [FilterAction.PERMABAN,FilterAction.REMBAN,FilterAction.BAN30,FilterAction.BAN7]:
                            expires = None
                            if tfilter.filter_action == FilterAction.BAN30:
                                expires = datetime.utcnow() + timedelta(days=30)
                            if tfilter.filter_action == FilterAction.BAN7:
                                expires = datetime.utcnow() + timedelta(days=7)
                            remove_all=False
                            if tfilter.filter_action == FilterAction.REMBAN:
                                remove_all=True
                            logger.info(f"Banned {user_url} for {tfilter.filter_action.name}")
                            webhook_parser(f"Banned {user_url} for {tfilter.filter_action.name}")
                            self.lemmy.user.ban(
                                ban=True,
                                expires=expires,
                                person_id=post["creator"]["id"],
                                reason=(
                                    f"Threativore automatic ban from report: {tfilter.reason}",
                                    f"Appeal by sending PM with your reasoning and including the text: `threativore request appeal {new_match.id}`",
                                ),
                                remove_data=remove_all,
                            )
                            entity_banned = True

            seen_post = Seen(
                entity_id=post_id,
                entity_type=EntityType.POST,
                entity_url=post["post"]["ap_id"],
            )
            db.session.add(seen_post)
            db.session.commit()
        return (seen_any_previously,all_ids)

    def check_pms(self):
        logger.debug("Checking PMs...")
        pms = self.lemmy.private_message.list(
            unread_only=True,
            limit=20,
            page=1,
        )
        if pms is None:
            return
        # logger.info(json.dumps(pms, indent=4))

        for pm in pms["private_messages"]:
            if "threativore" not in pm["private_message"]["content"].lower():
                continue
            try:
                filter_search = re.search(
                    r"(add|remove|show|modify) (report|comment|url) filter: ?`(.+?)`[ \n]*?",
                    pm["private_message"]["content"],
                    re.IGNORECASE,
                )
                if filter_search:
                    self.filters.parse_filter_pm(filter_search, pm)
                filter_list = re.search(r"list (report|comment) filters", pm["private_message"]["content"], re.IGNORECASE)
                if filter_list:
                    self.filters.parse_filter_list_pm(filter_list, pm)
                user_search = re.search(r"(add|remove) user: ?(.+)[ \n]*?", pm["private_message"]["content"], re.IGNORECASE)
                if user_search:
                    self.users.parse_user_pm(user_search, pm)
                request_appeal_search = re.search(
                    r"request appeal:? ?(\d+)",
                    pm["private_message"]["content"],
                    re.IGNORECASE,
                )
                if request_appeal_search:
                    self.appeals.parse_appeal_request(request_appeal_search, pm)
                restore_appeal_search = re.search(
                    r"appeal (reject|ignore):? ?(\d+)",
                    pm["private_message"]["content"],
                    re.IGNORECASE,
                )
                if request_appeal_search:
                    self.appeals.parse_appeal_restore(restore_appeal_search, pm)
            except e.ReplyException as err:
                self.reply_to_pm(
                    pm=pm,
                    message=(f"Problem encountered when parsing operation: {err}"),
                )
                logger.warning(err)  # TODO: Reply back
            except (e.ThreativoreException, e.DBException) as err:
                logger.error(err)

    def reply_to_pm(self, pm, message):
        self.reply_to_user_id(pm["private_message"]["creator_id"],message)
        self.lemmy.private_message.mark_as_read(pm["private_message"]["id"], True)

    def reply_to_user_id(self, user_id, message):
        self.lemmy.private_message.create(
            recipient_id=user_id,
            content=message,
        )

    def gc(self):
        rows_deleted = database.delete_seen_rows(args.gc_days)
        logger.debug(f"Deleting {rows_deleted} Seen rows")
        db.session.commit()