"""Comparação linear das relações, sem acesso à rede ou à interface."""

from .models import Analysis, Relationships


def analyze(data: Relationships) -> Analysis:
    return Analysis(
        followers=data.followers,
        following=data.following,
        not_following_back=data.following - data.followers,
        not_followed_back=data.followers - data.following,
        mutual=data.followers & data.following,
    )
