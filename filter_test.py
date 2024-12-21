import regex as re
import time
from threativore import threativore
from threativore.enums import UserRoleTypes
from threativore.flask import APP
from threativore.enums import FilterAction, FilterType
from loguru import logger
import threativore.database as database

# threativore()
with APP.app_context():
    try:
        threativore.filters.add_filter(
            filter='Test Appeals Filter', 
            user_url='https://lemmy.dbzer0.com/u/db0', 
            reason="Testing", 
            filter_action=FilterAction.REMOVE, 
            filter_type=FilterType.COMMENT
        )
    except Exception as err:
        logger.info(err)
    threativore.filters.print_all_filters()
    # print(database.actor_bypasses_filter("https://lemmy.dbzer0.com/u/randomleg"))
    # threativore.check_pms()
    # threativore.check_posts()
    # threativore.check_comments()
    # threativore.resolve_reports()
    comment_filters = database.get_all_filters(FilterType.COMMENT)
    comment_filters = database.get_all_filters(FilterType.REPORT)
    username_filters = database.get_all_filters(FilterType.USERNAME)
    # sorted_filters = sorted(comment_filters + username_filters, key=lambda x: x.filter_action.value)    
    # for tfilter in sorted_filters:
    #     filter_match = re.search(tfilter.regex, "Buy Modvigil 200mg Tablets Online At Health Matter", re.IGNORECASE)
    #     print([tfilter.regex,filter_match]) 
    pass

# strting = f"\\bBuy.+mg.+Online\\b"
# filter_match = re.search(strting, "Buy Modvigil 200mg Tablets Online At Health Matter", re.IGNORECASE)
# print(filter_match)