import os
from datetime import datetime, timedelta
from typing import Any

import regex as re
from loguru import logger

import threagetarian.database as database
import threagetarian.exceptions as e
from threagetarian.classes.filters import ThreagetarianFilters
from threagetarian.classes.users import ThreagetarianUsers
from threagetarian.enums import EntityType, FilterAction, FilterType, UserRoleTypes
from threagetarian.flask import APP, db
from threagetarian.orm.filters import FilterMatch
from threagetarian.orm.seen import Seen
from threagetarian.orm.user import User
from pythorhead.types.sort import CommentSortType


class Threagetarian:
    def __init__(self, _base_lemmy):
        self.lemmy = _base_lemmy.lemmy
        self.filters = ThreagetarianFilters(self)
        self.users = ThreagetarianUsers(self)
        self.ensure_admin_exists()

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        pass

    @logger.catch(reraise=True)
    def ensure_admin_exists(self):
        with APP.app_context():
            admin_user_url = os.getenv("THREAGETARIAN_ADMIN_URL")
            if not admin_user_url:
                raise e.ThreagetarianException("THREAGETARIAN_ADMIN_URL env not set")
            admin = database.get_user(admin_user_url)
            if not admin:
                admin = User(user_url=admin_user_url)
                db.session.add(admin)
                db.session.commit()
            admin.add_role(UserRoleTypes.ADMIN)

    def resolve_reports(self):
        logger.debug("Checking Reports...")
        self.resolve_post_reports()
        self.resolve_comment_reports()

    def resolve_comment_reports(self):
        rl = self.lemmy.comment.report_list(unresolved_only=False, limit=5)
        # logger.info(json.dumps(rl, indent=4))
        comment_filters = database.get_all_filters(FilterType.REPORT)
        username_filters = database.get_all_filters(FilterType.USERNAME)
        sorted_filters = sorted(comment_filters + username_filters, key=lambda x: x.filter_action.value)
        for report in rl:
            entity_removed = False
            entity_banned = False
            report_id: int = report["comment_report"]["id"]
            if database.has_been_seen(report_id, EntityType.REPORT):
                continue
            for tfilter in sorted_filters:
                if entity_removed:
                    break
                matching_string = ""
                if tfilter.filter_type == FilterType.REPORT:
                    filter_match = re.search(tfilter.regex, report["comment"]["content"], re.IGNORECASE)
                    matching_string = f'comment body: {report["comment"]["content"]}'
                if tfilter.filter_type == FilterType.USERNAME:
                    filter_match = re.search(tfilter.regex, report["creator"]["name"], re.IGNORECASE)
                    matching_string = f'commenter username: {report["creator"]["name"]}'
                if filter_match:
                    logger.info(f"Matched anti-spam filter for reported {matching_string} " f"regex: {filter_match}")
                    if tfilter.filter_action != FilterAction.REPORT:
                        logger.warning("Would remove comment from report")
                        self.lemmy.comment.remove(
                            comment_id=report["comment"]["id"],
                            removed=True,
                            reason=f"Threagetarian automatic comment removal: {tfilter.reason}",
                        )
                        entity_removed = True
                        try:
                            new_match = FilterMatch(
                                actor_id=report["comment_creator"]["actor_id"],
                                entity_id=report["comment"]["id"],
                                report_id=report_id,
                                url=report["comment"]["ap_id"],
                                filter_id=tfilter.id,
                            )
                            db.session.add(new_match)
                            db.session.commit()
                        except Exception as err:
                            logger.error(f"Error when commiting comment report FilterMatch: {err}")
                        if not entity_banned and tfilter.filter_action in [FilterAction.PERMABAN,FilterAction.BAN30,FilterAction.BAN7]:
                            expires = None
                            if tfilter.filter_action == FilterAction.BAN30:
                                expires = datetime.utcnow() + timedelta(days=30)
                            if tfilter.filter_action == FilterAction.BAN7:
                                expires = datetime.utcnow() + timedelta(days=7)
                            logger.warning(f"Would ban for {expires}")
                            # self.lemmy.user.ban(
                            #     ban=True,
                            #     expires=expires,
                            #     person_id=report["comment_creator"]["id"],
                            #     reason=f"Threagetarian automatic ban from comment report: {tfilter.reason}"
                            # )
                            entity_banned = True
                        # self.lemmy.comment.resolve_report(report["comment_report"]["id"])
            seen_report = Seen(
                entity_id=report_id,
                entity_type=EntityType.REPORT,
                entity_url=report["comment"]["ap_id"],
            )
            db.session.add(seen_report)
            db.session.commit()

    def resolve_post_reports(self):
        rl = self.lemmy.post.report_list()
        # logger.info(json.dumps(rl, indent=4))
        body_filters = database.get_all_filters(FilterType.REPORT)
        url_filters = database.get_all_filters(FilterType.URL)
        username_filters = database.get_all_filters(FilterType.USERNAME)
        sorted_filters = sorted(body_filters + url_filters + username_filters, key=lambda x: x.filter_action.value)
        for report in rl:
            entity_removed = False
            entity_banned = False
            report_id: int = report["post_report"]["id"]
            if database.has_been_seen(report_id, EntityType.REPORT):
                continue
            for tfilter in sorted_filters:
                if entity_removed:
                    break
                matched_filter = False
                matching_string = ""
                if tfilter.filter_type == FilterType.REPORT:
                    filter_match = re.search(tfilter.regex, report["post"]["name"], re.IGNORECASE)
                    if filter_match:
                        matched_filter = True
                        matching_string = f'post title: {report["post"]["name"]}'
                    elif "body" in report["post"]:
                        filter_match = re.search(tfilter.regex, report["post"]["body"], re.IGNORECASE)
                        if filter_match:
                            matched_filter = True
                            matching_string = f'post body: {report["post"]["body"]}'
                if "url" in report["post"] and tfilter.filter_type == FilterType.URL:
                    filter_match = re.search(tfilter.regex, report["post"]["url"], re.IGNORECASE)
                    if filter_match:
                        matched_filter = True
                        matching_string = f'post url: {report["post"]["url"]}'
                if tfilter.filter_type == FilterType.USERNAME:
                    filter_match = re.search(tfilter.regex, report["post_creator"]["name"], re.IGNORECASE)
                    if filter_match:
                        matched_filter = True
                        matching_string = f'poster username: {report["post_creator"]["name"]}'
                if matched_filter:
                    logger.info(f"Matched anti-spam filter for reported {matching_string} " f"regex: {filter_match}")
                    if tfilter.filter_action != FilterAction.REPORT:
                        logger.warning("Would remove post from report")
                        self.lemmy.post.remove(
                            post_id=report["post"]["id"],
                            removed=True,
                            reason=f"Threagetarian automatic post removal: {tfilter.reason}",
                        )
                        entity_removed = True
                        try:
                            new_match = FilterMatch(
                                actor_id=report["post_creator"]["actor_id"],
                                entity_id=report["post"]["id"],
                                report_id=report_id,
                                url=report["post"]["ap_id"],
                                filter_id=tfilter.id,
                            )
                            db.session.add(new_match)
                            db.session.commit()
                        except Exception as err:
                            logger.error(f"Error when commiting post FilterMatch: {err}")
                        if not entity_banned and tfilter.filter_action in [FilterAction.PERMABAN,FilterAction.BAN30,FilterAction.BAN7]:
                            expires = None
                            if tfilter.filter_action == FilterAction.BAN30:
                                expires = datetime.utcnow() + timedelta(days=30)
                            if tfilter.filter_action == FilterAction.BAN7:
                                expires = datetime.utcnow() + timedelta(days=7)
                            logger.warning(f"Would ban for {expires}")
                            # self.lemmy.user.ban(
                            #     ban=True,
                            #     expires=expires,
                            #     person_id=report["post_creator"]["id"],
                            #     reason=f"Threagetarian automatic ban from post report: {tfilter.reason}"
                            # )
                            entity_banned = True
                        # self.lemmy.comment.resolve_report(report["post_report"]["id"])
            seen_report = Seen(
                entity_id=report_id,
                entity_type=EntityType.REPORT,
                entity_url=report["post"]["ap_id"],
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
            for tfilter in sorted_filters:
                if entity_removed:
                    break
                if entity_reported and tfilter.filter_action == FilterAction.REPORT:
                    continue
                if tfilter.filter_type == FilterType.COMMENT:
                    filter_match = re.search(tfilter.regex, comment["comment"]["content"], re.IGNORECASE)
                    matching_string = f'comment body: {comment["comment"]["content"]}'
                if tfilter.filter_type == FilterType.USERNAME:
                    filter_match = re.search(tfilter.regex, comment["creator"]["name"], re.IGNORECASE)
                    matching_string = f'commenter username: {comment["creator"]["name"]}'
                # logger.info([comment["comment"]["content"], f.regex])
                if filter_match:
                    logger.info(f"Matched anti-spam filter for {matching_string} " f"regex: {filter_match}")
                    # Comments
                    try:
                        new_match = FilterMatch(
                            actor_id=comment["creator"]["actor_id"],
                            entity_id=comment_id,
                            url=comment["comment"]["ap_id"],
                            filter_id=tfilter.id,
                        )
                        db.session.add(new_match)
                        db.session.commit()
                    except Exception as err:
                        logger.error(f"Error when commiting comment FilterMatch: {err}")
                    if tfilter.filter_action == FilterAction.REPORT:
                        self.lemmy.comment.report(
                            comment_id=comment_id,
                            reason=f"Threagetarian automatic comment: {tfilter.reason}",
                        )
                        entity_reported = True
                    else:
                        # BETA TESTING ONLY
                        logger.warning("Would remove comment")
                        logger.debug(f"Reported {comment_id}")
                        self.lemmy.comment.report(
                            comment_id=comment_id,
                            reason=f"Threagetarian automatic beta testing report: {tfilter.reason}",
                        )
                        entity_reported = True

                        # self.lemmy.comment.remove(
                        #     comment_id=comment_id,
                        #     removed=True,
                        #     reason=f"Threagetarian automatic comment removal: {tfilter.reason}",
                        # )
                        entity_removed = True
                        if not entity_banned and tfilter.filter_action in [FilterAction.PERMABAN,FilterAction.BAN30,FilterAction.BAN7]:
                            expires = None
                            if tfilter.filter_action == FilterAction.BAN30:
                                expires = datetime.utcnow() + timedelta(days=30)
                            if tfilter.filter_action == FilterAction.BAN7:
                                expires = datetime.utcnow() + timedelta(days=7)
                            logger.warning(f"Would ban for {expires}")
                            # self.lemmy.user.ban(
                            #     ban=True,
                            #     expires=expires,
                            #     person_id=comment["creator"]["id"],
                            #     reason=f"Threagetarian automatic ban from post: {tfilter.reason}"
                            # )
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

            entity_removed = False
            entity_reported = False
            entity_banned = False
            for tfilter in sorted_filters:
                if entity_removed:
                    break
                if entity_reported and tfilter.filter_action == FilterAction.REPORT:
                    continue
                matched_filter = False
                if tfilter.filter_type == FilterType.COMMENT:
                    filter_match = re.search(tfilter.regex, post["post"]["name"], re.IGNORECASE)
                    if matched_filter:
                        matched_filter = True
                        matching_string = f'post title: {post["post"]["name"]}'
                    elif "body" in post["post"]:
                        filter_match = re.search(tfilter.regex, post["post"]["body"], re.IGNORECASE)
                        if matched_filter:
                            matched_filter = True
                            matching_string = f'post body: {post["post"]["body"]}'
                if "url" in post["post"] and tfilter.filter_type == FilterType.URL:
                    filter_match = re.search(tfilter.regex, post["post"]["url"], re.IGNORECASE)
                    if filter_match:
                        matched_filter = True
                        matching_string = f'post url: {post["post"]["url"]}'
                if tfilter.filter_type == FilterType.USERNAME:
                    filter_match = re.search(tfilter.regex, post["creator"]["name"], re.IGNORECASE)
                    if filter_match:
                        matched_filter = True
                        matching_string = f'poster username: {post["creator"]["name"]}'
                # logger.info([comment["comment"]["content"], f.regex])
                if matched_filter:
                    logger.info(f"Matched anti-spam filter for {matching_string} " f"regex: {filter_match}")
                    try:
                        new_match = FilterMatch(
                            actor_id=post["creator"]["actor_id"],
                            entity_id=post_id,
                            url=post["post"]["ap_id"],
                            filter_id=tfilter.id,
                        )
                        db.session.add(new_match)
                        db.session.commit()
                    except Exception as err:
                        logger.error(f"Error when commiting post FilterMatch: {err}")
                    if tfilter.filter_action == FilterAction.REPORT:
                        self.lemmy.post.report(
                            comment_id=post_id,
                            reason=f"Threagetarian automatic post report: {tfilter.reason}",
                        )
                        entity_reported = True
                    else:
                        # BETA TESTING ONLY
                        logger.warning("Would remove post")
                        self.lemmy.post.report(
                            comment_id=post_id,
                            reason=f"Threagetarian automatic beta testing report: {tfilter.reason}",
                        )
                        entity_reported = True
                        # self.lemmy.comment.remove(
                        #     comment_id=post_id,
                        #     removed=True,
                        #     reason=f"Threagetarian automatic post removal: {tfilter.reason}",
                        # )
                        entity_removed = True
                        if not entity_banned and tfilter.filter_action in [FilterAction.PERMABAN,FilterAction.BAN30,FilterAction.BAN7]:
                            expires = None
                            if tfilter.filter_action == FilterAction.BAN30:
                                expires = datetime.utcnow() + timedelta(days=30)
                            if tfilter.filter_action == FilterAction.BAN7:
                                expires = datetime.utcnow() + timedelta(days=7)
                            logger.warning(f"Would ban for {expires}")
                            # self.lemmy.user.ban(
                            #     ban=True,
                            #     expires=expires,
                            #     person_id=post["creator"]["id"],
                            #     reason=f"Threagetarian automatic ban from report: {tfilter.reason}"
                            # )
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
            if "threagetarian" not in pm["private_message"]["content"].lower():
                continue
            try:
                filter_search = re.search(
                    r"(add|remove|show|modify) (report|comment) filter: ?`(.+?)`[ \n]*?",
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
            except e.ReplyException as err:
                self.reply_to_pm(
                    pm=pm,
                    message=(f"Problem encountered when parsing operation: {err}"),
                )
                logger.warning(err)  # TODO: Reply back
            except (e.ThreagetarianException, e.DBException) as err:
                logger.error(err)

    def reply_to_pm(self, pm, message):
        self.lemmy.private_message.create(
            recipient_id=pm["private_message"]["creator_id"],
            content=message,
        )
        self.lemmy.private_message.mark_as_read(pm["private_message"]["id"], True)
