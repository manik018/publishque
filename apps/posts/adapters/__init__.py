from .facebook import FacebookAdapter
from .linkedin import LinkedInAdapter
from .pinterest import PinterestAdapter


def get_adapter_for_platform(platform):
    if platform == "facebook":
        return FacebookAdapter()
    if platform == "linkedin":
        return LinkedInAdapter()
    if platform == "pinterest":
        return PinterestAdapter()
    raise NotImplementedError(f"No publishing adapter is configured for {platform}.")
