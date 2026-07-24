import logging

from .base import BasePlatformAdapter


logger = logging.getLogger("publishque.posts.adapters.pinterest")


class PinterestAdapter(BasePlatformAdapter):
    def publish(self, post_target):
        # TODO: implement real Pinterest API call.
        logger.info(
            "Publishing post target %s to Pinterest profile %s",
            post_target.pk,
            post_target.connected_profile.platform_account_id,
        )
        return True
