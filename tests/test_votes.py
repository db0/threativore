import regex as re
import time
from threativore.main import threativore
from threativore.enums import UserRoleTypes
from threativore.flask import APP
from threativore.enums import FilterAction, FilterType
from loguru import logger
import threativore.database as database
import random

with APP.app_context():
    gpost = database.get_governance_post('https://lemmy.dbzer0.com/post/60724228')
    db0 = database.get_user("https://lemmy.dbzer0.com/u/db0")
    # db0.add_alias("https://anarchist.nexus/u/db0")
    for gpost in database.get_all_active_governance_posts():
        logger.info(gpost.get_details())
    if not gpost:
        logger.error("No governance post found")
        exit(1)
    # logger.info(threativore.governance.compile_voting_tallies(gpost))
    votes = []
    valid_votes: list[dict] = []
    # We use this for deduplication of confed votes
    valid_voted_set = set()
    local_non_votes = []
    external_non_votes = []
    more_votes = []
    page = 1 
    while len(more_votes) >= 50 or page == 1:
        if threativore.governance.threativore.lemmy.post.list_votes(gpost.post_id, page=page) is None:
            break        
        more_votes = threativore.governance.threativore.lemmy.post.list_votes(gpost.post_id, page=page).get("post_likes", [])
        page += 1
        votes += more_votes
    for v in votes:
        voting_user = database.get_user(v["creator"]["actor_id"].lower())
        if threativore.governance.is_admin(v["creator"]["actor_id"].lower()) and not voting_user:
            voting_user = threativore.governance.threativore.users.ensure_user_exists(v["creator"]["actor_id"].lower())
        # If it's a confed user, this might be a known alias, so we check if we find one
        if not voting_user and threativore.governance.is_confed(v["creator"]["actor_id"].lower()):
            voting_user = database.get_user_from_alias(v["creator"]["actor_id"].lower())
        # If any alias of this user has already voted, we disregard potential multiple votes.
        if voting_user in valid_voted_set:
            logger.warning(f"Duplicate vote from {voting_user.user_url}")
            continue
        if voting_user and (voting_user.can_vote() or threativore.governance.is_admin(voting_user.user_url)):
            valid_voted_set.add(voting_user)
            logger.info(f'Proper Voting: {v["creator"]["actor_id"].lower()}')
            valid_votes.append(
                {
                    "user": voting_user,
                    "score": v["score"]
                }
            )
        elif v["creator"]["local"]:
            local_non_votes.append(v["score"])
            logger.info(f'Local Vote: {v["creator"]["actor_id"].lower()}')
        elif threativore.governance.is_confed(v["creator"]["actor_id"]):
            local_non_votes.append(v["score"])
            logger.info(f'Confed Vote: {v["creator"]["actor_id"].lower()}')
        else:
            external_non_votes.append(v["score"])
    # We only take a sample from the local and externals
    random.shuffle(local_non_votes)
    local_non_votes = local_non_votes[:1000]
    local_non_voter_tally = sum(local_non_votes) if local_non_votes else 0
    logger.info(f"local_non_voter_tally: {local_non_voter_tally}")
    logger.info(f"external_non_votes: {external_non_votes}")
    local_non_voter_tally_str = ""
    # For local non-voters, we add one vote per 100 from the sample (so maximum +/- 10)
    if local_non_voter_tally > 0: 
        local_non_voter_tally = round(local_non_voter_tally/100,1)
        local_non_voter_tally_str = f"+{local_non_voter_tally}"
    elif local_non_voter_tally < 0:
        local_non_voter_tally = round(local_non_voter_tally/100,1)
        local_non_voter_tally_str = str(local_non_voter_tally)
    external_sentiment = ""
    positive_external_votes = sum([1 for vote in external_non_votes if vote > 0])
    negative_external_votes = sum([1 for vote in external_non_votes if vote < 0])
    external_non_votes_sum = sum(external_non_votes)
    if len(external_non_votes) > 10 and abs(positive_external_votes - negative_external_votes) <= 3:
        external_sentiment = "Controversial"
    elif external_non_votes_sum > 0:
        external_sentiment = "Sympathetic"
        if external_non_votes_sum >= 10:
            external_sentiment = "Positive"
        if external_non_votes_sum >= 50:
            external_sentiment = "Very Positive"
        if external_non_votes_sum >= 100:
            external_sentiment = "Supportive"
        if external_non_votes_sum >= 1000:
            external_sentiment = "Solidarity"
    elif external_non_votes_sum < 0:
        external_sentiment = "Skeptical"
        if external_non_votes_sum <= -10:
            external_sentiment = "Negative"
        if external_non_votes_sum <= -50:
            external_sentiment = "Very Negative"
        if external_non_votes_sum <= -100:
            external_sentiment = "Critical"
        if external_non_votes_sum <= -1000:
            external_sentiment = "Resistance"
    logger.info(f"local_non_voter_tally: {local_non_voter_tally}")
    logger.info(f"external_non_votes: {external_non_votes}")
    logger.info(f"external_sentiment: {external_sentiment}")
