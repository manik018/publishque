from .pinterest import PinterestAdapter


def get_adapter_for_platform(platform):
    if platform == "pinterest":
        return PinterestAdapter()
    raise NotImplementedError(f"No publishing adapter is configured for {platform}.")
