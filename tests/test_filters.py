import regex as re
import time
from threativore.main import threativore
from threativore.enums import UserRoleTypes
from threativore.flask import APP
from threativore.enums import FilterAction, FilterType
from loguru import logger
import threativore.database as database

@logger.catch
def test_filters():
    with APP.app_context():
        # threativore.filters.add_filter(
        #     filter='Test Appeals Filter', 
        #     user_url='https://lemmy.dbzer0.com/u/db0', 
        #     reason="Testing", 
        #     filter_action=FilterAction.REMOVE, 
        #     filter_type=FilterType.COMMENT
        # )
        # threativore.filters.modify_filter(
        #     existing_filter_id='13', 
        #     user_url='https://lemmy.dbzer0.com/u/db0', 
        #     filter_action=FilterAction.REPORT,
        #     reason="Testing", 
        # )
        pm = {
            "private_message":{"content":"threativore modify comment filter: `13` action: `REMOVE`"},
            "creator": {"actor_id":"https://lemmy.dbzer0.com/u/db0"}
        }
        filter_search = re.search(
            r"(add|remove|show|modify) (report|comment|url) filter: ?`(.+?)`[ \n]*?",
            "threativore modify comment filter: `13` action: `REMOVE`",
            re.IGNORECASE,
        )
        threativore.filters.parse_filter_pm(filter_search, pm)        
        # except Exception as err:
        #     logger.info(err)
        threativore.filters.print_all_filters()
        # print(database.actor_bypasses_filter("https://lemmy.dbzer0.com/u/randomleg"))
        # threativore.check_pms()
        # threativore.check_posts()
        # threativore.check_comments()
        # threativore.resolve_reports()
        comment_filters = database.get_all_filters(FilterType.COMMENT)
        comment_filters = database.get_all_filters(FilterType.REPORT)
        username_filters = database.get_all_filters(FilterType.USERNAME)
        pass

# print(filter_match)

test_filters()