from django.urls import path
from .views import (
    search_view, simple_search_view,
    ai_parse_query, ai_suggest, ai_summary,
    ai_search_page, ai_rag_search,
    browse_by_keyword, browse_by_location,
)

app_name = "search"

urlpatterns = [
    path("", search_view, name="search"),
    path("simple/", simple_search_view, name="simple_search"),
    path("browse/keyword/", browse_by_keyword, name="browse_by_keyword"),
    path("browse/location/", browse_by_location, name="browse_by_location"),
    # AI search page & API
    path("ai-search/", ai_search_page, name="ai_search"),
    path("api/ai-search/", ai_rag_search, name="ai_rag_search"),
    # AI search utility endpoints
    path("api/ai-parse/", ai_parse_query, name="ai_parse_query"),
    path("api/ai-suggest/", ai_suggest, name="ai_suggest"),
    path("api/ai-summary/", ai_summary, name="ai_summary"),
]

