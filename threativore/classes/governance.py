import regex as re
import time
from loguru import logger
from threativore.config import Config
from pythorhead.types.sort import CommentSortType, SortType
import threativore.database as database
from threativore.orm.governance import GovernancePost, GovernancePostComment
from threativore.orm.user import User
from datetime import datetime, timedelta
from threativore.flask import APP, db
from threativore.enums import GovernancePostType
from threativore import utils
from threativore.emoji import lemmy_emoji
from threativore.argparser import args
import threading
import random

class Governance:
    
    governance_community_id: int = None
    site_admins = set()

    def __init__(self, threativore):
        self.threativore = threativore
        if Config.governance_community:
            self.governance_community_id = self.threativore.lemmy.discover_community(Config.governance_community)
        if not self.governance_community_id:
            logger.warning("Governance community not set or not found. Governance module will be inactive")
            return
        self.governance_tasks = threading.Thread(target=self.governance_tasks, args=(), daemon=True)
        self.governance_tasks.start()

    def check_for_new_posts(self):
        logger.debug(f"Checking for new Governance posts")
        gp = self.threativore.lemmy.post.list(community_id = self.governance_community_id, limit=10,sort=SortType.New)
        for post in gp:
            post_id = post["post"]["id"]
            if post["post"]["removed"] is True:
                continue
            if post["post"]["locked"] is True:
                continue
            if post["post"]["deleted"] is True:
                continue
            existing_gpost = database.get_governance_post(post_id)
            if not existing_gpost:
                body = post["post"].get("body", '')
                expiry = 7
                expiry_regex = re.search(
                    r"expiry:? ?(\d+)",
                    body,
                    re.IGNORECASE,
                )
                if expiry_regex:
                    expiry = int(expiry_regex.group(1))
                if expiry > 30:
                    expiry == 30
                if expiry < 1:
                    expiry == 1
                user_url = post["creator"]["actor_id"].lower()
                user: User | None = database.get_user(user_url)
                if not user:
                    user = self.threativore.users.ensure_user_exists(user_url)
                post_type = GovernancePostType.SIMPLE_MAJORITY
                post_type_regex = re.search(
                    r"governance type:? ?(simple majority voting|voting|sense check|discussion)",
                    body,
                    re.IGNORECASE,
                )
                if post_type_regex:
                    if post_type_regex.group(1).lower == "sense check":
                        post_type = GovernancePostType.SENSE_CHECK
                    elif post_type_regex.group(1).lower in ["simple majority voting", "voting", "simple majority"]:
                        post_type = GovernancePostType.SIMPLE_MAJORITY
                    else: 
                        post_type = GovernancePostType.OTHER
                new_gpost = GovernancePost(
                    post_id = post_id,
                    user_id = user.id,
                    expires = datetime.utcnow() + timedelta(days=expiry),
                    upvotes = post["counts"]["upvotes"],
                    downvotes = post["counts"]["downvotes"],
                    post_type = post_type,
                    newest_comment_time = datetime.fromisoformat(post["counts"]["newest_comment_time"].replace('Z', '+00:00')) if post["counts"]["newest_comment_time"] else datetime.utcnow(),
                )
                db.session.add(new_gpost)
                db.session.commit()
                if not user.can_vote():
                    self.adjust_control_comment_on_gpost(new_gpost, "This user is not trusted by this instance and therefore cannot initiate new governance posts")
                    self.lock_gpost(new_gpost, "Threativore automatic post removal: Governance post with empty body")
                    self.remove_gpost(new_gpost, "Threativore automatic post removal: Governance post by untrusted user")
                    continue
                if not body:
                    self.adjust_control_comment_on_gpost(new_gpost, "You cannot open a governance post with an empty body.")
                    self.lock_gpost(new_gpost, "Threativore automatic post removal: Governance post with empty body")
                    self.remove_gpost(new_gpost, "Threativore automatic post removal: Governance post with empty body")
                    continue
                self.adjust_control_comment_on_gpost(
                    gpost=new_gpost, 
                    content=self.get_standard_gpost_control_comment(gpost=new_gpost, user=user)
                )
                
            
    def adjust_control_comment_on_gpost(self, gpost: GovernancePost, content: str):
        if gpost.control_comment_id is None:
            comment = self.threativore.lemmy.comment.create(
                post_id = gpost.post_id,
                content = content
            )
            gpost.control_comment_id = comment["comment_view"]["comment"]["id"]
            db.session.commit()
            self.threativore.lemmy.comment.distinguish(gpost.control_comment_id, True)
        else:
            self.threativore.lemmy.comment.edit(
                comment_id = gpost.control_comment_id,
                content = content
            )

    def lock_gpost(self, gpost: GovernancePost):
        self.threativore.lemmy.post.lock(post_id=gpost.post_id, locked=True)
        gpost.expires = datetime.utcnow()
        db.session.commit()

    def remove_gpost(self, gpost: GovernancePost, reason: str):
        self.threativore.lemmy.post.remove(post_id=gpost.post_id, removed=True, reason=reason)
        gpost.expires = datetime.utcnow()
        db.session.commit()

    def get_standard_gpost_control_comment(self, gpost: GovernancePost, user: User) -> str:
        control_comment_text = f"Acknowledged governance topic opened by {user.user_url} {''.join(user.get_all_flair_markdowns())}"
        if self.is_admin(user.user_url):
            control_comment_text += lemmy_emoji.get_emoji_markdown(Config.admin_emoji)
        if gpost.post_type == GovernancePostType.SIMPLE_MAJORITY:
            control_comment_text += '\n\n ' + self.compile_voting_tallies(gpost)
        else:
            control_comment_text += '\n\n This is a non-voting post. Known users should leave comments with your thoughts on the subject.'
        return control_comment_text


    def compile_voting_tallies(self,gpost: GovernancePost) -> str:
        votes = []
        valid_votes: list[dict] = []
        local_non_votes = []
        external_non_votes = []
        more_votes = []
        page = 1 
        while len(more_votes) >= 50 or page == 1:
            more_votes = self.threativore.lemmy.post.list_votes(gpost.post_id, page=page).get("post_likes", [])
            page += 1
            votes += more_votes
        for v in votes:
            voting_user = database.get_user(v["creator"]["actor_id"].lower())
            if self.is_admin(v["creator"]["actor_id"].lower()) and not voting_user:
                voting_user = self.threativore.users.ensure_user_exists(v["creator"]["actor_id"].lower())
            if voting_user and (voting_user.can_vote() or self.is_admin(voting_user.user_url)):
                valid_votes.append(
                    {
                        "user": voting_user,
                        "score": v["score"]
                    }
                )
            elif v["creator"]["local"]:
                local_non_votes.append(v["score"])
            else:
                external_non_votes.append(v["score"])
        # We only take a sample from the local and externals
        random.shuffle(local_non_votes)
        local_non_votes = local_non_votes[:1000]
        local_non_voter_tally = sum(local_non_votes) if local_non_votes else 0
        local_non_voter_tally_str = ""
        # For local non-voters, we add one vote per 100 from the sample (so maximum +/- 10)
        if local_non_voter_tally > 0: 
            local_non_voter_tally = round(local_non_voter_tally/100,1)
            local_non_voter_tally_str = f"+{local_non_voter_tally}"
        elif local_non_voter_tally < 0:
            local_non_voter_tally = round(local_non_voter_tally/100,1)
            local_non_voter_tally_str = str(local_non_voter_tally)
        external_non_votes = sum(external_non_votes)
        external_sentiment = ""
        if external_non_votes > 0:
            external_sentiment = "Positive"
            if external_non_votes >= 100:
                external_sentiment = "Very Positive"
            if external_non_votes >= 1000:
                external_sentiment = "Extremely Positive"
        elif external_non_votes < 0:
            external_sentiment = "Negative"
            if external_non_votes <= 100:
                external_sentiment = "Very Negative"
            if external_non_votes <= 1000:
                external_sentiment = "Extremely Negative"
        downvote_flair_markdowns = []
        upvote_flair_markdowns = []
        def count_unique_flairs(flairs_list):
            string_counts = {}
            for string in flairs_list:
                if string in string_counts:
                    string_counts[string] += 1
                else:
                    string_counts[string] = 1
            return string_counts

        for v in valid_votes:
            flair_markdown = v["user"].get_most_significant_voting_flair_markdown()
            if self.is_admin(v["user"].user_url):
                flair_markdown = lemmy_emoji.get_emoji_markdown(Config.admin_emoji)
            if v["score"] == 1:
                upvote_flair_markdowns.append(flair_markdown)
            elif v["score"] == -1:
                downvote_flair_markdowns.append(flair_markdown)
        return_string = "This is a simple majority vote. The current tally is as follows: "
        if gpost.is_expired():
            return_string = "This is a simple majority vote. The final tally is as follows: "
        if len(upvote_flair_markdowns) > 10:
            upvote_flair_markdowns_counts = count_unique_flairs(upvote_flair_markdowns)
            return_string += '\n\n* For: ' + ', '.join([f"{key}({value})" for key, value in upvote_flair_markdowns_counts.items()])
        else:            
            return_string += '\n\n* For: ' + ''.join(upvote_flair_markdowns)
        if len(downvote_flair_markdowns) > 10:
            downvote_flair_markdowns_counts = count_unique_flairs(downvote_flair_markdowns)
            return_string += '\n* Against: ' + ', '.join([f"{key}({value})" for key, value in downvote_flair_markdowns_counts.items()])
        else:            
            return_string += '\n* Against: ' + ''.join(downvote_flair_markdowns)
        total = len(upvote_flair_markdowns) - len(downvote_flair_markdowns) + local_non_voter_tally
        if local_non_voter_tally:
            return_string += f"\n* Local Community: {local_non_voter_tally_str}"
        if external_sentiment:
            return_string += f"\n* Outsider sentiment: {external_sentiment}"
        if total > 0:
            total = f"+{total}"
        return_string += f"\n* Total: {total}"
        upvotes = len(upvote_flair_markdowns)
        upvotes += local_non_voter_tally
        downvotes = len(downvote_flair_markdowns)
        total_votes = upvotes + downvotes + local_non_voter_tally
        if total_votes > 0:
            percentage = (upvotes / total_votes) * 100
        else:
            percentage = 0
        return_string += f"\n* Percentage: {percentage:.2f}%"
        if gpost.is_expired():
            return_string += f"\n\n This vote has concluded on {gpost.expires.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        else:
            units_remaining = (gpost.expires - datetime.utcnow()).days
            tu = "days"
            if units_remaining < 1:
                units_remaining = (gpost.expires - datetime.utcnow()).seconds
                if units_remaining > 3600:
                    units_remaining = round(units_remaining / 3600, 2)
                    tu = "hours"
                else:
                    units_remaining = round(units_remaining / 60, 2)
                    tu = "minutes"
            return_string += f"\n\n This vote will complete in {units_remaining} {tu}"
        return_string += f"\n\n --- \n\n*Reminder that this is a pilot process and results of voting are not set in stone.*"
        return return_string

    def get_comment_flair(self, comment, show_all_flair: bool, redo_comment_flair: bool = False) -> str | None:
        "Returns a comment_markdown if markdown is valid. Else returns None"
        user_url = comment["creator"]["actor_id"].lower()
        if user_url == self.threativore.threativore_user_url:
            return
        if not redo_comment_flair and database.replied_to_gpost_comment(comment["comment"]["id"]):
            return
        comment_user: User = self.threativore.users.ensure_user_exists(user_url)
        if show_all_flair:
            flair_markdown = ''.join(comment_user.get_all_flair_markdowns())
        else:
            flair_markdown = comment_user.get_most_significant_voting_flair_markdown()
            flair_markdown += comment_user.get_most_significant_non_voting_flair_markdown()
        if not flair_markdown:
            flair_markdown = lemmy_emoji.get_emoji_markdown(Config.outsider_emoji)
        if self.is_admin(comment["creator"]["actor_id"].lower()): 
            if not show_all_flair:
                flair_markdown = lemmy_emoji.get_emoji_markdown(Config.admin_emoji)
            else:
                flair_markdown += lemmy_emoji.get_emoji_markdown(Config.admin_emoji)
        return flair_markdown

    def update_gpost(self, gpost: GovernancePost, redo_all_comment_flair:bool = False):
        gpost_info = self.threativore.lemmy.post.get(gpost.post_id)
        if gpost_info["post_view"]["post"]["removed"] is True:
            return
        if gpost_info["post_view"]["post"]["locked"] is True:
            return
        if gpost_info["post_view"]["post"]["deleted"] is True:
            return
        show_all_flair = False
        if re.search(r"show all flair", gpost_info["post_view"]["post"].get("body", ''), re.IGNORECASE):
            show_all_flair = True
        control_comment = self.get_standard_gpost_control_comment(gpost=gpost, user=gpost.user)
        self.adjust_control_comment_on_gpost(
            gpost=gpost, 
            content=control_comment
        )                
        if gpost.expires < datetime.utcnow():
            self.lock_gpost(gpost)
        comments = []
        # I wanted to do just 50 at a time, limit is ignored when max_depth is specified
        # Test command:
        # curl --request GET      --url 'https://lemmy.dbzer0.com/api/v3/comment/list?limit=10&max_depth=1&post_id=35858425'      --header 'accept: application/json' -s | jq '.comments[].comment.id'  | wc -l
        comments = self.threativore.lemmy.comment.list(
            post_id = gpost.post_id, 
            max_depth=1,
        )
        for comment in comments:
            flair_markdown = self.get_comment_flair(comment,show_all_flair, redo_all_comment_flair)
            if flair_markdown is None:
                continue
            if redo_all_comment_flair:
                existing_flair_comment = database.get_comment_flair_reply(comment["comment"]["id"])
                if existing_flair_comment:
                    logger.debug(f"Updating existing comment {existing_flair_comment.comment_id}")
                    flair_comment = self.threativore.lemmy.comment.edit(
                        comment_id = existing_flair_comment.comment_id,
                        content = flair_markdown,
                    )             
            else:
                logger.debug(f'Replying to root comment {comment["comment"]["id"]}')
                flair_comment = self.threativore.lemmy.comment.create(
                    post_id = gpost.post_id,
                    content = flair_markdown,
                    parent_id = comment["comment"]["id"]
                )
                new_gpost_comment_reply = GovernancePostComment(
                    parent_id = comment["comment"]["id"],
                    comment_id = flair_comment["comment_view"]["comment"]["id"],
                    gpost_id = gpost.id,
                    user_id = comment["creator"]["actor_id"].lower()
                )
                db.session.add(new_gpost_comment_reply)
                db.session.commit()        

    def update_gposts(self):
        logger.debug(f"Checking known Governance posts")
        for gpost in database.get_all_active_governance_posts():
            self.update_gpost(gpost)


    def update_single_comment_flair(self, parent_id):
        existing_flair_comment = database.get_comment_flair_reply(parent_id)
        if not existing_flair_comment:
             logger.error(f"No known reply for {parent_id}.")
             return
        parent = self.threativore.lemmy.comment.get(parent_id)
        flair_markdown = self.get_comment_flair(parent["comment_view"], False, True)
        if not flair_markdown:
            logger.error(f"comment {parent} has no flair markdown.")
            return
        self.threativore.lemmy.comment.edit(existing_flair_comment.comment_id, flair_markdown)
        logger.debug(flair_markdown)
        
    def full_update_single_gpost(self, gpost_id):
        gpost = database.get_gpost(gpost_id)
        self.update_gpost(gpost,redo_all_comment_flair=True)
        
    def parse_pm(self, pm):
        governance_thread_init_search = re.search(
            r"governance init thread:? ?(.*)",
            pm["private_message"]["content"],
            re.IGNORECASE,
        )
        if governance_thread_init_search:
            thread_content = governance_thread_init_search = re.search(
                r"content: (.*)",
                pm["private_message"]["content"],
                re.IGNORECASE,
                re.MULTILINE,
            )
            #TODO: Generate an image based on the title
        #TODO: Create thread. Store in DB.
        
    def is_admin(self, user_url):
        return user_url in self.site_admins

    def update_admins(self):
        site_admins = set()
        site_info = self.threativore.lemmy.site.get()
        for admin in site_info["admins"]:
            site_admins.add(admin["person"]["actor_id"].lower())
        self.site_admins = site_admins
        logger.debug(f"Site Admins: {self.site_admins}")
        

    @logger.catch(reraise=True)
    def governance_tasks(self):
        self.update_admins()
        with APP.app_context():
            if args.refresh_comment is not None:
                self.update_single_comment_flair(args.refresh_comment)
                exit(0)
            if args.refresh_all_gpost_comments is not None:
                self.full_update_single_gpost(args.refresh_all_gpost_comments)
                exit(0)
            while True:
                try:
                    self.update_gposts()
                    self.check_for_new_posts()
                    time.sleep(15*60)
                    self.update_admins()
                except Exception as err:
                    raise err
                    logger.warning(f"Exception during loop: {err}. Will continue after sleep...")
                    time.sleep(1)
