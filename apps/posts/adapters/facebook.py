import logging

from .base import BasePlatformAdapter


logger = logging.getLogger("publishque.posts.adapters.facebook")


class FacebookAdapter(BasePlatformAdapter):
    def publish(self, post_target):
        # TODO: implement real Facebook Graph API publish call.
        logger.info(
            "Facebook publish stub succeeded for post target %s and page %s",
            post_target.pk,
            post_target.connected_profile.platform_account_id,
        )
        return True
