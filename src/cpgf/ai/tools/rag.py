from __future__ import annotations


class RAGNotAvailableError(RuntimeError):
    """O RAG normativo será implementado em etapa própria."""


def retrieve_normative_sources(*_: object, **__: object) -> None:
    raise RAGNotAvailableError(
        "RAG normativo ainda não está habilitado. A fundação do PR #25 não consulta documentos."
    )
