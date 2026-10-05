"""Sorgu yeniden yazma (query rewriting).

Agent bunu search_company_policies aracını çağırırken zaten kendisi yapıyor.
Bu modül, aynı tekniğin etkisini agent'tan bağımsız olarak ölçebilmek için
eval_retrieval.py tarafından kullanılır.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.llm import get_llm
from src.prompts import load_prompt


class SearchQueries(BaseModel):
    queries: list[str] = Field(description="1-3 kısa arama ifadesi")


def rewrite_query(question: str) -> list[str]:
    llm = get_llm(temperature=0).with_structured_output(SearchQueries)
    result = llm.invoke([
        SystemMessage(content=load_prompt("query_rewrite")),
        HumanMessage(content=question),
    ])
    return result.queries[:3]