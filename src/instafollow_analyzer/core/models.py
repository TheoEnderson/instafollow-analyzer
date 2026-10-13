"""Tipos imutáveis compartilhados pelo parser, analisador e exportador."""

from dataclasses import dataclass


class DataError(Exception):
    """Falha de entrada/saída cuja mensagem pode ser apresentada ao usuário."""


@dataclass(frozen=True)
class Relationships:
    followers: frozenset[str]
    following: frozenset[str]


@dataclass(frozen=True)
class Analysis:
    followers: frozenset[str]
    following: frozenset[str]
    not_following_back: frozenset[str]
    not_followed_back: frozenset[str]
    mutual: frozenset[str]

    def categories(self) -> dict[str, frozenset[str]]:
        return {
            "nao_me_seguem_de_volta": self.not_following_back,
            "nao_sigo_de_volta": self.not_followed_back,
            "seguimento_mutuo": self.mutual,
        }


def profile_url(username: str) -> str:
    return f"https://www.instagram.com/{username}/"
