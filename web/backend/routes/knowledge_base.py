"""Knowledge Base CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: Optional[str] = "#06b6d4"


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = None


class TagResponse(BaseModel):
    id: int
    name: str
    color: Optional[str] = "#06b6d4"


class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)
    category_id: Optional[int] = None
    tag_ids: list[int] = []
    author: Optional[str] = None
    is_published: bool = False


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    content: Optional[str] = None
    category_id: Optional[int] = None
    tag_ids: Optional[list[int]] = None
    author: Optional[str] = None
    is_published: Optional[bool] = None


class ArticleResponse(BaseModel):
    id: int
    title: str
    content: str
    category_id: Optional[int] = None
    tag_ids: list[int] = []
    author: Optional[str] = None
    is_published: bool = False
    views: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CommentCreate(BaseModel):
    article_id: int
    author: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)


class CommentUpdate(BaseModel):
    content: Optional[str] = None


class CommentResponse(BaseModel):
    id: int
    article_id: int
    author: str
    content: str
    created_at: Optional[str] = None


# ─── In-Memory Data Stores ────────────────────────────────────────────────────

_categories_db = [
    {"id": 1, "name": "Getting Started", "description": "Onboarding and setup guides"},
    {"id": 2, "name": "API Reference", "description": "API documentation and examples"},
    {"id": 3, "name": "Troubleshooting", "description": "Common issues and solutions"},
]
_tags_db = [
    {"id": 1, "name": "beginner", "color": "#22c55e"},
    {"id": 2, "name": "advanced", "color": "#f59e0b"},
    {"id": 3, "name": "deprecated", "color": "#ef4444"},
]
_articles_db = [
    {
        "id": 1,
        "title": "Welcome to APEX-OS",
        "content": "APEX-OS is a comprehensive business platform...",
        "category_id": 1,
        "tag_ids": [1],
        "author": "Admin",
        "is_published": True,
        "views": 152,
        "created_at": "2026-09-01T10:00:00",
        "updated_at": "2026-09-01T10:00:00",
    },
    {
        "id": 2,
        "title": "API Authentication Guide",
        "content": "All API requests require an X-API-Key header...",
        "category_id": 2,
        "tag_ids": [1, 2],
        "author": "Admin",
        "is_published": True,
        "views": 89,
        "created_at": "2026-09-05T14:30:00",
        "updated_at": "2026-09-05T14:30:00",
    },
    {
        "id": 3,
        "title": "Troubleshooting Common Issues",
        "content": "If you encounter issues, check the following...",
        "category_id": 3,
        "tag_ids": [2],
        "author": "Support",
        "is_published": True,
        "views": 45,
        "created_at": "2026-09-10T09:15:00",
        "updated_at": "2026-09-10T09:15:00",
    },
]
_comments_db = [
    {"id": 1, "article_id": 1, "author": "User1", "content": "Great intro!", "created_at": "2026-09-02T08:00:00"},
    {"id": 2, "article_id": 1, "author": "User2", "content": "Very helpful, thanks.", "created_at": "2026-09-03T12:00:00"},
]

_next_category_id = 4
_next_tag_id = 4
_next_article_id = 4
_next_comment_id = 3


# ─── Category Endpoints ───────────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories():
    """List all categories."""
    return _categories_db


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int):
    """Get a single category by ID."""
    for cat in _categories_db:
        if cat["id"] == category_id:
            return cat
    raise HTTPException(status_code=404, detail="Category not found")


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(category: CategoryCreate):
    """Create a new category."""
    global _next_category_id
    new_cat = {"id": _next_category_id, **category.model_dump()}
    _categories_db.append(new_cat)
    _next_category_id += 1
    return new_cat


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: int, category: CategoryUpdate):
    """Update an existing category."""
    for idx, existing in enumerate(_categories_db):
        if existing["id"] == category_id:
            updated = existing.copy()
            updated.update({k: v for k, v in category.model_dump().items() if v is not None})
            _categories_db[idx] = updated
            return updated
    raise HTTPException(status_code=404, detail="Category not found")


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int):
    """Delete a category by ID."""
    for idx, cat in enumerate(_categories_db):
        if cat["id"] == category_id:
            _categories_db.pop(idx)
            return
    raise HTTPException(status_code=404, detail="Category not found")


# ─── Tag Endpoints ────────────────────────────────────────────────────────────

@router.get("/tags", response_model=list[TagResponse])
async def list_tags():
    """List all tags."""
    return _tags_db


@router.get("/tags/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int):
    """Get a single tag by ID."""
    for tag in _tags_db:
        if tag["id"] == tag_id:
            return tag
    raise HTTPException(status_code=404, detail="Tag not found")


@router.post("/tags", response_model=TagResponse, status_code=201)
async def create_tag(tag: TagCreate):
    """Create a new tag."""
    global _next_tag_id
    new_tag = {"id": _next_tag_id, **tag.model_dump()}
    _tags_db.append(new_tag)
    _next_tag_id += 1
    return new_tag


@router.put("/tags/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: int, tag: TagUpdate):
    """Update an existing tag."""
    for idx, existing in enumerate(_tags_db):
        if existing["id"] == tag_id:
            updated = existing.copy()
            updated.update({k: v for k, v in tag.model_dump().items() if v is not None})
            _tags_db[idx] = updated
            return updated
    raise HTTPException(status_code=404, detail="Tag not found")


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: int):
    """Delete a tag by ID."""
    for idx, tag in enumerate(_tags_db):
        if tag["id"] == tag_id:
            _tags_db.pop(idx)
            return
    raise HTTPException(status_code=404, detail="Tag not found")


# ─── Article Endpoints ────────────────────────────────────────────────────────

@router.get("/articles", response_model=list[ArticleResponse])
async def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
):
    """List articles with optional filtering by category and search."""
    results = _articles_db[skip : skip + limit]
    if category_id is not None:
        results = [a for a in results if a.get("category_id") == category_id]
    if search:
        q = search.lower()
        results = [
            a for a in results
            if q in a["title"].lower() or q in a["content"].lower()
        ]
    return results


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int):
    """Get a single article by ID."""
    for article in _articles_db:
        if article["id"] == article_id:
            return article
    raise HTTPException(status_code=404, detail="Article not found")


@router.post("/articles", response_model=ArticleResponse, status_code=201)
async def create_article(article: ArticleCreate):
    """Create a new article."""
    global _next_article_id
    from datetime import datetime
    now = datetime.now().isoformat()
    new_article = {
        "id": _next_article_id,
        **article.model_dump(),
        "views": 0,
        "created_at": now,
        "updated_at": now,
    }
    _articles_db.append(new_article)
    _next_article_id += 1
    return new_article


@router.put("/articles/{article_id}", response_model=ArticleResponse)
async def update_article(article_id: int, article: ArticleUpdate):
    """Update an existing article."""
    from datetime import datetime
    for idx, existing in enumerate(_articles_db):
        if existing["id"] == article_id:
            updated = existing.copy()
            updated.update({k: v for k, v in article.model_dump().items() if v is not None})
            updated["updated_at"] = datetime.now().isoformat()
            _articles_db[idx] = updated
            return updated
    raise HTTPException(status_code=404, detail="Article not found")


@router.delete("/articles/{article_id}", status_code=204)
async def delete_article(article_id: int):
    """Delete an article by ID."""
    for idx, article in enumerate(_articles_db):
        if article["id"] == article_id:
            _articles_db.pop(idx)
            return
    raise HTTPException(status_code=404, detail="Article not found")


# ─── Comment Endpoints ────────────────────────────────────────────────────────

@router.get("/comments", response_model=list[CommentResponse])
async def list_comments(article_id: Optional[int] = None):
    """List comments, optionally filtered by article."""
    if article_id is not None:
        return [c for c in _comments_db if c["article_id"] == article_id]
    return _comments_db


@router.get("/comments/{comment_id}", response_model=CommentResponse)
async def get_comment(comment_id: int):
    """Get a single comment by ID."""
    for comment in _comments_db:
        if comment["id"] == comment_id:
            return comment
    raise HTTPException(status_code=404, detail="Comment not found")


@router.post("/comments", response_model=CommentResponse, status_code=201)
async def create_comment(comment: CommentCreate):
    """Create a new comment."""
    global _next_comment_id
    from datetime import datetime
    new_comment = {
        "id": _next_comment_id,
        **comment.model_dump(),
        "created_at": datetime.now().isoformat(),
    }
    _comments_db.append(new_comment)
    _next_comment_id += 1
    return new_comment


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(comment_id: int, comment: CommentUpdate):
    """Update an existing comment."""
    for idx, existing in enumerate(_comments_db):
        if existing["id"] == comment_id:
            updated = existing.copy()
            updated.update({k: v for k, v in comment.model_dump().items() if v is not None})
            _comments_db[idx] = updated
            return updated
    raise HTTPException(status_code=404, detail="Comment not found")


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: int):
    """Delete a comment by ID."""
    for idx, comment in enumerate(_comments_db):
        if comment["id"] == comment_id:
            _comments_db.pop(idx)
            return
    raise HTTPException(status_code=404, detail="Comment not found")
