import json
from pythonseer.types import FormatType
from threativore.config import Config
import time
import threading
from loguru import logger
from pythonseer import Fediseer
from threativore.orm.keystore import KeyStore
from threativore.flask import APP, db


class ThreativoreFediseer:

    def __init__(self, _base_lemmy, _threativore):
        self.lemmy = _base_lemmy.lemmy
        self.fediseer = Fediseer()
        self.threativore = _threativore
        if Config.fediseer_api_key:
            self.fediseer.log_in(Config.fediseer_api_key)
        self.standard_tasks = threading.Thread(target=self.standard_tasks, args=(), daemon=True)
        self.standard_tasks.start()

    def standard_tasks(self):
      with APP.app_context():        
        while True:
            try:
                self.refresh_blocklist()
                time.sleep(600)
            except Exception as err:
                logger.warning(f"Exception during loop: {err}. Will continue after sleep...")
                time.sleep(600)

    def refresh_blocklist(self):
        if KeyStore.get_validating_blocklist():
            logger.warning("Validating blocklist is set. Not refreshing blocklist this loop...")
            return
        logger.info("Starting blocklist refresh...")

        # Fetching suspicions
        sus = self.fediseer.suspicions.get(
            activity_suspicion=Config.fediseer_sus_users_per_activity,
            active_suspicion=Config.fediseer_sus_activity_per_user,
            format=FormatType.LIST
        )

        # Fetching trusted censures
        trusted_instances = set(Config.fediseer_trusted_instances)
        trusted_instances.add(Config.lemmy_domain)
        trusted_censures = self.fediseer.censure.get_given(
            domain_set=trusted_instances,
            min_censures=Config.fediseer_min_censures,
            format=FormatType.LIST,
        )

        # Fetching filtered censures
        filtered_censures = self.fediseer.censure.get_given(
            domain_set=set(Config.fediseer_filtered_instances),
            reasons=Config.fediseer_reason_filters,
            min_censures=Config.fediseer_min_censures,
            format=FormatType.LIST,
        )

        # Fetching endorsements
        endorsements = self.fediseer.endorsement.get_given(
            domain_set=trusted_instances,
            format=FormatType.LIST,
        )

        # Calculate the new blocklist
        defed = (
            set(Config.fediseer_adhoc_blocks) |
            set(trusted_censures["domains"]) |
            set(filtered_censures["domains"]) |
            set(sus["domains"])
        ) - set(Config.fediseer_safelist) - set(endorsements["domains"])

        # Load previous blocklist
        prev_defed =  KeyStore.get_previous_blocklist()
        if not prev_defed:
            logger.warning("Previous defed file doesn't exist. Will probably receive a warning about blocklist.")
            prev_defed = set()

        # Log changes
        new_blocks = defed - prev_defed
        removed_blocks = prev_defed - defed
        if new_blocks:
            logger.info(f"New blocks to add: {new_blocks}")
        if removed_blocks:
            logger.info(f"Blocks to remove: {removed_blocks}")
        if not new_blocks and not removed_blocks:
            logger.info("No changes to the blocklist.")
            return

        # Warn if changes exceed threshold
        if len(new_blocks) + len(removed_blocks) >= Config.fediseer_changes_warning_threshold:
            logger.warning(
                f"{len(new_blocks) + len(removed_blocks)} changes to blocklist detected. DMing admin"
            )
            new_blocks_list = "\n".join(f"- {block}" for block in new_blocks)
            removed_blocks_list = "\n".join(f"- {block}" for block in removed_blocks)
            message = (
              f"Warning! You are about to make {len(new_blocks) + len(removed_blocks)} changes to your blocklist.\n\n"
              f"**New blocks:**\n\n{new_blocks_list}\n\n"
              f"**Removed blocks:**\n\n{removed_blocks_list}\n\n"
              "**Please review the changes before proceeding.**\n\n"
              "If approved, reply with `threativore approve pending blocklist` "
              "else reply `threativore reject pending blocklist`"
            )
            self.threativore.reply_to_user_url(Config.threativore_admin_url, message)
            return

        # Retrieve site info for application question
        site = self.lemmy.site.get()
        # I need to retrieve the site info because it seems if "RequireApplication" is set
        # We need to always re-set the application_question. 
        # So we retrieve it from the existing site, to set the same value        
        application_question = None
        if site["site_view"]["local_site"]["registration_mode"] == "RequireApplication":
            application_question = site["site_view"]["local_site"]["application_question"]

        # Update blocklist
        logger.info("Editing defederation list...")
        # if application_question:
        #     ret = self.lemmy.site.edit(
        #         blocked_instances=list(defed),
        #         application_question=application_question,
        #     )
        # else:
        #     ret = self.lemmy.site.edit(
        #         blocked_instances=list(defed),
        #     )

        # if ret is None:
        #     logger.error("Blocklist update failed!")
        # else:
        #     logger.info("Blocklist update successful.")
        #     KeyStore.set_keyvalue('previous_blocklist', json.dumps(list(defed)))
