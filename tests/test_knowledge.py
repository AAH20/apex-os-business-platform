"""Tests for knowledge management system."""
import pytest
from apex_os_bp.knowledge import (
    DocumentSearch,
    DocumentType,
    ExpertFinder,
    ExpertiseLevel,
    KnowledgeBase,
    KnowledgeGraph,
    RecommendationEngine,
)


# ── Knowledge Base Tests ──


class TestKnowledgeBase:
    """Test knowledge base functionality."""

    def test_add_item(self):
        """Item can be added to knowledge base."""
        kb = KnowledgeBase()
        item = kb.add_item(
            title="Python Best Practices",
            content="Follow PEP 8 guidelines",
            category="engineering",
            tags=["python", "best-practices"],
        )
        assert item.id is not None
        assert item.title == "Python Best Practices"
        assert item.content == "Follow PEP 8 guidelines"
        assert item.category == "engineering"
        assert "python" in item.tags

    def test_get_item(self):
        """Item can be retrieved by ID."""
        kb = KnowledgeBase()
        item = kb.add_item(title="Test", content="Content", category="test")
        retrieved = kb.get_item(item.id)
        assert retrieved is not None
        assert retrieved.title == "Test"

    def test_get_item_not_found(self):
        """Returns None for non-existent item."""
        kb = KnowledgeBase()
        assert kb.get_item("nonexistent") is None

    def test_update_item(self):
        """Item can be updated."""
        kb = KnowledgeBase()
        item = kb.add_item(title="Old Title", content="Content", category="test")
        updated = kb.update_item(item.id, title="New Title")
        assert updated is not None
        assert updated.title == "New Title"

    def test_update_item_not_found(self):
        """Returns None when updating non-existent item."""
        kb = KnowledgeBase()
        assert kb.update_item("nonexistent", title="New") is None

    def test_delete_item(self):
        """Item can be deleted."""
        kb = KnowledgeBase()
        item = kb.add_item(title="Test", content="Content", category="test")
        assert kb.delete_item(item.id) is True
        assert kb.get_item(item.id) is None

    def test_delete_item_not_found(self):
        """Returns False when deleting non-existent item."""
        kb = KnowledgeBase()
        assert kb.delete_item("nonexistent") is False

    def test_get_all_items(self):
        """All items can be retrieved."""
        kb = KnowledgeBase()
        kb.add_item(title="Item 1", content="Content 1", category="cat1")
        kb.add_item(title="Item 2", content="Content 2", category="cat2")
        items = kb.get_all_items()
        assert len(items) == 2

    def test_get_by_category(self):
        """Items can be filtered by category."""
        kb = KnowledgeBase()
        kb.add_item(title="Item 1", content="Content", category="engineering")
        kb.add_item(title="Item 2", content="Content", category="marketing")
        kb.add_item(title="Item 3", content="Content", category="engineering")
        items = kb.get_by_category("engineering")
        assert len(items) == 2

    def test_get_by_tag(self):
        """Items can be filtered by tag."""
        kb = KnowledgeBase()
        kb.add_item(title="Item 1", content="Content", category="cat", tags=["python"])
        kb.add_item(title="Item 2", content="Content", category="cat", tags=["java"])
        kb.add_item(title="Item 3", content="Content", category="cat", tags=["python", "coding"])
        items = kb.get_by_tag("python")
        assert len(items) == 2

    def test_get_by_author(self):
        """Items can be filtered by author."""
        kb = KnowledgeBase()
        kb.add_item(title="Item 1", content="Content", category="cat", author_id="user-1")
        kb.add_item(title="Item 2", content="Content", category="cat", author_id="user-2")
        items = kb.get_by_author("user-1")
        assert len(items) == 1

    def test_count(self):
        """Count returns correct number of items."""
        kb = KnowledgeBase()
        assert kb.count() == 0
        kb.add_item(title="Item", content="Content", category="cat")
        assert kb.count() == 1

    def test_categories(self):
        """All unique categories are returned."""
        kb = KnowledgeBase()
        kb.add_item(title="Item 1", content="Content", category="engineering")
        kb.add_item(title="Item 2", content="Content", category="marketing")
        kb.add_item(title="Item 3", content="Content", category="engineering")
        cats = kb.categories()
        assert len(cats) == 2
        assert "engineering" in cats
        assert "marketing" in cats

    def test_all_tags(self):
        """All unique tags are returned."""
        kb = KnowledgeBase()
        kb.add_item(title="Item 1", content="Content", category="cat", tags=["python", "coding"])
        kb.add_item(title="Item 2", content="Content", category="cat", tags=["java", "coding"])
        tags = kb.all_tags()
        assert len(tags) == 3
        assert "python" in tags
        assert "java" in tags
        assert "coding" in tags


# ── Document Search Tests ──


class TestDocumentSearch:
    """Test document search functionality."""

    def test_add_document(self):
        """Document can be added to search index."""
        ds = DocumentSearch()
        doc = ds.add_document(
            title="Python Guide",
            content="Python is a programming language",
            doc_type=DocumentType.GUIDE,
        )
        assert doc.id is not None
        assert doc.title == "Python Guide"
        assert doc.doc_type == DocumentType.GUIDE

    def test_get_document(self):
        """Document can be retrieved by ID."""
        ds = DocumentSearch()
        doc = ds.add_document(title="Test", content="Content")
        retrieved = ds.get_document(doc.id)
        assert retrieved is not None
        assert retrieved.title == "Test"

    def test_get_document_not_found(self):
        """Returns None for non-existent document."""
        ds = DocumentSearch()
        assert ds.get_document("nonexistent") is None

    def test_delete_document(self):
        """Document can be deleted."""
        ds = DocumentSearch()
        doc = ds.add_document(title="Test", content="Content")
        assert ds.delete_document(doc.id) is True
        assert ds.get_document(doc.id) is None

    def test_search_basic(self):
        """Basic search returns relevant results."""
        ds = DocumentSearch()
        ds.add_document(title="Python Tutorial", content="Learn Python programming")
        ds.add_document(title="Java Guide", content="Java programming guide")
        results = ds.search("Python")
        assert len(results) >= 1
        assert results[0].document.title == "Python Tutorial"
        assert results[0].score > 0

    def test_search_empty_query(self):
        """Empty query returns no results."""
        ds = DocumentSearch()
        ds.add_document(title="Test", content="Content")
        assert ds.search("") == []

    def test_search_no_match(self):
        """Non-matching query returns no results."""
        ds = DocumentSearch()
        ds.add_document(title="Python", content="Programming")
        assert ds.search("nonexistent") == []

    def test_search_by_type(self):
        """Documents can be filtered by type."""
        ds = DocumentSearch()
        ds.add_document(title="Doc 1", content="Content", doc_type=DocumentType.ARTICLE)
        ds.add_document(title="Doc 2", content="Content", doc_type=DocumentType.GUIDE)
        ds.add_document(title="Doc 3", content="Content", doc_type=DocumentType.ARTICLE)
        results = ds.search_by_type(DocumentType.ARTICLE)
        assert len(results) == 2

    def test_search_by_tag(self):
        """Documents can be filtered by tag."""
        ds = DocumentSearch()
        ds.add_document(title="Doc 1", content="Content", tags=["python"])
        ds.add_document(title="Doc 2", content="Content", tags=["java"])
        results = ds.search_by_tag("python")
        assert len(results) == 1

    def test_search_limit(self):
        """Search respects limit parameter."""
        ds = DocumentSearch()
        for i in range(10):
            ds.add_document(title=f"Python Doc {i}", content="Python content")
        results = ds.search("Python", limit=3)
        assert len(results) == 3

    def test_search_highlights(self):
        """Search results include highlights."""
        ds = DocumentSearch()
        ds.add_document(title="Python", content="Python is great for programming")
        results = ds.search("Python")
        assert len(results) > 0
        assert len(results[0].highlights) > 0

    def test_search_sorted_by_score(self):
        """Results are sorted by relevance score."""
        ds = DocumentSearch()
        ds.add_document(title="Python Python Python", content="Python Python")
        ds.add_document(title="Java", content="Java programming")
        results = ds.search("Python")
        assert len(results) >= 1
        assert results[0].score >= results[-1].score

    def test_count(self):
        """Count returns correct number of documents."""
        ds = DocumentSearch()
        assert ds.count() == 0
        ds.add_document(title="Doc", content="Content")
        assert ds.count() == 1

    def test_get_all_documents(self):
        """All documents can be retrieved."""
        ds = DocumentSearch()
        ds.add_document(title="Doc 1", content="Content 1")
        ds.add_document(title="Doc 2", content="Content 2")
        docs = ds.get_all_documents()
        assert len(docs) == 2


# ── Expert Finder Tests ──


class TestExpertFinder:
    """Test expert finder functionality."""

    def test_add_expert(self):
        """Expert can be added."""
        ef = ExpertFinder()
        expert = ef.add_expert(
            name="Alice Smith",
            email="alice@example.com",
            skills=["Python", "Machine Learning"],
            expertise_level=ExpertiseLevel.EXPERT,
            department="Engineering",
        )
        assert expert.id is not None
        assert expert.name == "Alice Smith"
        assert expert.email == "alice@example.com"
        assert "Python" in expert.skills
        assert expert.expertise_level == ExpertiseLevel.EXPERT
        assert expert.available is True

    def test_get_expert(self):
        """Expert can be retrieved by ID."""
        ef = ExpertFinder()
        expert = ef.add_expert(name="Bob", email="bob@example.com")
        retrieved = ef.get_expert(expert.id)
        assert retrieved is not None
        assert retrieved.name == "Bob"

    def test_get_expert_not_found(self):
        """Returns None for non-existent expert."""
        ef = ExpertFinder()
        assert ef.get_expert("nonexistent") is None

    def test_update_expert(self):
        """Expert can be updated."""
        ef = ExpertFinder()
        expert = ef.add_expert(name="Alice", email="alice@example.com", available=True)
        updated = ef.update_expert(expert.id, available=False)
        assert updated is not None
        assert updated.available is False

    def test_update_expert_not_found(self):
        """Returns None when updating non-existent expert."""
        ef = ExpertFinder()
        assert ef.update_expert("nonexistent", name="New") is None

    def test_delete_expert(self):
        """Expert can be deleted."""
        ef = ExpertFinder()
        expert = ef.add_expert(name="Alice", email="alice@example.com")
        assert ef.delete_expert(expert.id) is True
        assert ef.get_expert(expert.id) is None

    def test_delete_expert_not_found(self):
        """Returns False when deleting non-existent expert."""
        ef = ExpertFinder()
        assert ef.delete_expert("nonexistent") is False

    def test_find_by_skill(self):
        """Experts can be found by skill."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python", "ML"])
        ef.add_expert(name="Bob", email="bob@example.com", skills=["Java", "Spring"])
        results = ef.find_by_skill("Python")
        assert len(results) == 1
        assert results[0].name == "Alice"

    def test_find_by_skill_case_insensitive(self):
        """Skill search is case-insensitive."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python"])
        results = ef.find_by_skill("python")
        assert len(results) == 1

    def test_find_by_skill_unavailable(self):
        """Unavailable experts are excluded when available_only=True."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python"], available=False)
        results = ef.find_by_skill("Python", available_only=True)
        assert len(results) == 0

    def test_find_by_skill_include_unavailable(self):
        """Unavailable experts are included when available_only=False."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python"], available=False)
        results = ef.find_by_skill("Python", available_only=False)
        assert len(results) == 1

    def test_find_by_skills_match_all(self):
        """Find experts matching all skills."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python", "ML", "Docker"])
        ef.add_expert(name="Bob", email="bob@example.com", skills=["Python", "Java"])
        results = ef.find_by_skills(["Python", "ML"], match_all=True)
        assert len(results) == 1
        assert results[0].name == "Alice"

    def test_find_by_skills_match_any(self):
        """Find experts matching any skill."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python"])
        ef.add_expert(name="Bob", email="bob@example.com", skills=["Java"])
        ef.add_expert(name="Charlie", email="charlie@example.com", skills=["Go"])
        results = ef.find_by_skills(["Python", "Java"], match_all=False)
        assert len(results) == 2

    def test_find_by_department(self):
        """Experts can be found by department."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", department="Engineering")
        ef.add_expert(name="Bob", email="bob@example.com", department="Marketing")
        results = ef.find_by_department("Engineering")
        assert len(results) == 1

    def test_find_by_expertise(self):
        """Experts can be found by expertise level."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", expertise_level=ExpertiseLevel.EXPERT)
        ef.add_expert(name="Bob", email="bob@example.com", expertise_level=ExpertiseLevel.NOVICE)
        results = ef.find_by_expertise(ExpertiseLevel.EXPERT)
        assert len(results) == 1

    def test_get_all_experts(self):
        """All experts can be retrieved."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com")
        ef.add_expert(name="Bob", email="bob@example.com")
        assert len(ef.get_all_experts()) == 2

    def test_get_available_experts(self):
        """Only available experts are returned."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", available=True)
        ef.add_expert(name="Bob", email="bob@example.com", available=False)
        results = ef.get_available_experts()
        assert len(results) == 1
        assert results[0].name == "Alice"

    def test_count(self):
        """Count returns correct number of experts."""
        ef = ExpertFinder()
        assert ef.count() == 0
        ef.add_expert(name="Alice", email="alice@example.com")
        assert ef.count() == 1

    def test_all_skills(self):
        """All unique skills are returned."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python", "ML"])
        ef.add_expert(name="Bob", email="bob@example.com", skills=["Java", "ML"])
        skills = ef.all_skills()
        assert len(skills) == 3

    def test_all_departments(self):
        """All unique departments are returned."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", department="Engineering")
        ef.add_expert(name="Bob", email="bob@example.com", department="Marketing")
        depts = ef.all_departments()
        assert len(depts) == 2


# ── Knowledge Graph Tests ──


class TestKnowledgeGraph:
    """Test knowledge graph functionality."""

    def test_add_node(self):
        """Node can be added to graph."""
        kg = KnowledgeGraph()
        node = kg.add_node(label="Python", node_type="technology")
        assert node.id is not None
        assert node.label == "Python"
        assert node.node_type == "technology"

    def test_get_node(self):
        """Node can be retrieved by ID."""
        kg = KnowledgeGraph()
        node = kg.add_node(label="Python", node_type="technology")
        retrieved = kg.get_node(node.id)
        assert retrieved is not None
        assert retrieved.label == "Python"

    def test_get_node_not_found(self):
        """Returns None for non-existent node."""
        kg = KnowledgeGraph()
        assert kg.get_node("nonexistent") is None

    def test_update_node(self):
        """Node can be updated."""
        kg = KnowledgeGraph()
        node = kg.add_node(label="Old", node_type="type")
        updated = kg.update_node(node.id, label="New")
        assert updated is not None
        assert updated.label == "New"

    def test_update_node_not_found(self):
        """Returns None when updating non-existent node."""
        kg = KnowledgeGraph()
        assert kg.update_node("nonexistent", label="New") is None

    def test_delete_node(self):
        """Node can be deleted."""
        kg = KnowledgeGraph()
        node = kg.add_node(label="Test", node_type="type")
        assert kg.delete_node(node.id) is True
        assert kg.get_node(node.id) is None

    def test_delete_node_not_found(self):
        """Returns False when deleting non-existent node."""
        kg = KnowledgeGraph()
        assert kg.delete_node("nonexistent") is False

    def test_add_edge(self):
        """Edge can be added between nodes."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="Python", node_type="language")
        n2 = kg.add_node(label="Django", node_type="framework")
        edge = kg.add_edge(n1.id, n2.id, relation="used_by")
        assert edge.id is not None
        assert edge.source_id == n1.id
        assert edge.target_id == n2.id
        assert edge.relation == "used_by"

    def test_add_edge_invalid_source(self):
        """Raises error for invalid source node."""
        kg = KnowledgeGraph()
        n2 = kg.add_node(label="Target", node_type="type")
        with pytest.raises(ValueError):
            kg.add_edge("nonexistent", n2.id, relation="rel")

    def test_add_edge_invalid_target(self):
        """Raises error for invalid target node."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="Source", node_type="type")
        with pytest.raises(ValueError):
            kg.add_edge(n1.id, "nonexistent", relation="rel")

    def test_get_edge(self):
        """Edge can be retrieved by ID."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        edge = kg.add_edge(n1.id, n2.id, relation="rel")
        retrieved = kg.get_edge(edge.id)
        assert retrieved is not None
        assert retrieved.relation == "rel"

    def test_delete_edge(self):
        """Edge can be deleted."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        edge = kg.add_edge(n1.id, n2.id, relation="rel")
        assert kg.delete_edge(edge.id) is True
        assert kg.get_edge(edge.id) is None

    def test_delete_edge_not_found(self):
        """Returns False when deleting non-existent edge."""
        kg = KnowledgeGraph()
        assert kg.delete_edge("nonexistent") is False

    def test_get_neighbors(self):
        """Neighbors of a node can be retrieved."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        n3 = kg.add_node(label="C", node_type="type")
        kg.add_edge(n1.id, n2.id, relation="rel")
        kg.add_edge(n1.id, n3.id, relation="rel")
        neighbors = kg.get_neighbors(n1.id)
        assert len(neighbors) == 2

    def test_get_edges_from(self):
        """Edges from a node can be retrieved."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        n3 = kg.add_node(label="C", node_type="type")
        kg.add_edge(n1.id, n2.id, relation="rel1")
        kg.add_edge(n1.id, n3.id, relation="rel2")
        edges = kg.get_edges_from(n1.id)
        assert len(edges) == 2

    def test_get_edges_to(self):
        """Edges to a node can be retrieved."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        n3 = kg.add_node(label="C", node_type="type")
        kg.add_edge(n1.id, n3.id, relation="rel1")
        kg.add_edge(n2.id, n3.id, relation="rel2")
        edges = kg.get_edges_to(n3.id)
        assert len(edges) == 2

    def test_find_path(self):
        """Path between nodes can be found."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        n3 = kg.add_node(label="C", node_type="type")
        kg.add_edge(n1.id, n2.id, relation="rel")
        kg.add_edge(n2.id, n3.id, relation="rel")
        path = kg.find_path(n1.id, n3.id)
        assert path is not None
        assert len(path) == 3
        assert path[0].label == "A"
        assert path[2].label == "C"

    def test_find_path_same_node(self):
        """Path from node to itself returns single node."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        path = kg.find_path(n1.id, n1.id)
        assert path is not None
        assert len(path) == 1

    def test_find_path_no_path(self):
        """Returns None when no path exists."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        path = kg.find_path(n1.id, n2.id)
        assert path is None

    def test_find_path_invalid_node(self):
        """Returns None for invalid node IDs."""
        kg = KnowledgeGraph()
        assert kg.find_path("a", "b") is None

    def test_search_nodes(self):
        """Nodes can be searched by label."""
        kg = KnowledgeGraph()
        kg.add_node(label="Python", node_type="language")
        kg.add_node(label="Java", node_type="language")
        kg.add_node(label="PythonScript", node_type="tool")
        results = kg.search_nodes("Python")
        assert len(results) == 2

    def test_search_nodes_by_type(self):
        """Nodes can be filtered by type during search."""
        kg = KnowledgeGraph()
        kg.add_node(label="Python", node_type="language")
        kg.add_node(label="Python", node_type="tool")
        results = kg.search_nodes("Python", node_type="language")
        assert len(results) == 1

    def test_get_nodes_by_type(self):
        """Nodes can be filtered by type."""
        kg = KnowledgeGraph()
        kg.add_node(label="A", node_type="language")
        kg.add_node(label="B", node_type="framework")
        kg.add_node(label="C", node_type="language")
        results = kg.get_nodes_by_type("language")
        assert len(results) == 2

    def test_node_count(self):
        """Node count is correct."""
        kg = KnowledgeGraph()
        assert kg.node_count() == 0
        kg.add_node(label="A", node_type="type")
        assert kg.node_count() == 1

    def test_edge_count(self):
        """Edge count is correct."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        assert kg.edge_count() == 0
        kg.add_edge(n1.id, n2.id, relation="rel")
        assert kg.edge_count() == 1

    def test_get_all_nodes(self):
        """All nodes can be retrieved."""
        kg = KnowledgeGraph()
        kg.add_node(label="A", node_type="type")
        kg.add_node(label="B", node_type="type")
        assert len(kg.get_all_nodes()) == 2

    def test_get_all_edges(self):
        """All edges can be retrieved."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        kg.add_edge(n1.id, n2.id, relation="rel1")
        kg.add_edge(n2.id, n1.id, relation="rel2")
        assert len(kg.get_all_edges()) == 2

    def test_get_relation_types(self):
        """All unique relation types are returned."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        kg.add_edge(n1.id, n2.id, relation="uses")
        kg.add_edge(n2.id, n1.id, relation="depends_on")
        kg.add_edge(n1.id, n2.id, relation="uses")
        rels = kg.get_relation_types()
        assert len(rels) == 2

    def test_delete_node_removes_edges(self):
        """Deleting a node also removes connected edges."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="A", node_type="type")
        n2 = kg.add_node(label="B", node_type="type")
        kg.add_edge(n1.id, n2.id, relation="rel")
        assert kg.edge_count() == 1
        kg.delete_node(n1.id)
        assert kg.edge_count() == 0


# ── Recommendation Engine Tests ──


class TestRecommendationEngine:
    """Test recommendation engine functionality."""

    def test_record_interaction(self):
        """User interaction can be recorded."""
        re = RecommendationEngine()
        re.record_interaction("user-1", "item-1")
        history = re.get_user_history("user-1")
        assert "item-1" in history

    def test_get_user_history_empty(self):
        """Returns empty list for unknown user."""
        re = RecommendationEngine()
        assert re.get_user_history("unknown") == []

    def test_recommend_for_user(self):
        """Recommendations are generated based on user history."""
        kb = KnowledgeBase()
        item1 = kb.add_item(title="Python Basics", content="Content", category="engineering", tags=["python"])
        item2 = kb.add_item(title="Advanced Python", content="Content", category="engineering", tags=["python", "advanced"])
        item3 = kb.add_item(title="Marketing 101", content="Content", category="marketing", tags=["marketing"])

        re = RecommendationEngine(knowledge_base=kb)
        re.record_interaction("user-1", item1.id)

        recs = re.recommend_for_user("user-1")
        assert len(recs) > 0
        # item2 should be recommended (shares python tag)
        rec_ids = [r.item_id for r in recs]
        assert item2.id in rec_ids

    def test_recommend_for_user_no_history(self):
        """No recommendations for user with no history."""
        kb = KnowledgeBase()
        kb.add_item(title="Item", content="Content", category="cat")
        re = RecommendationEngine(knowledge_base=kb)
        recs = re.recommend_for_user("user-1")
        assert len(recs) == 0

    def test_recommend_documents(self):
        """Documents can be recommended based on query."""
        ds = DocumentSearch()
        ds.add_document(title="Python Guide", content="Python programming guide")
        ds.add_document(title="Java Guide", content="Java programming guide")

        re = RecommendationEngine(document_search=ds)
        recs = re.recommend_documents("Python")
        assert len(recs) > 0
        assert recs[0].item_type == "document"

    def test_recommend_experts(self):
        """Experts can be recommended based on skills."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python", "ML"], expertise_level=ExpertiseLevel.EXPERT)
        ef.add_expert(name="Bob", email="bob@example.com", skills=["Java"], expertise_level=ExpertiseLevel.NOVICE)

        re = RecommendationEngine(expert_finder=ef)
        recs = re.recommend_experts(["Python"])
        assert len(recs) > 0
        assert recs[0].item_type == "expert"

    def test_recommend_experts_scoring(self):
        """Expert recommendations are scored correctly."""
        ef = ExpertFinder()
        ef.add_expert(name="Alice", email="alice@example.com", skills=["Python", "ML"], expertise_level=ExpertiseLevel.EXPERT)
        ef.add_expert(name="Bob", email="bob@example.com", skills=["Python"], expertise_level=ExpertiseLevel.NOVICE)

        re = RecommendationEngine(expert_finder=ef)
        recs = re.recommend_experts(["Python"])
        assert len(recs) == 2
        # Alice should score higher (expert level + more skill matches)
        assert recs[0].score >= recs[1].score

    def test_recommend_related(self):
        """Related items can be recommended via knowledge graph."""
        kg = KnowledgeGraph()
        n1 = kg.add_node(label="Python", node_type="language")
        n2 = kg.add_node(label="Django", node_type="framework")
        n3 = kg.add_node(label="Flask", node_type="framework")
        kg.add_edge(n1.id, n2.id, relation="used_by", weight=2.0)
        kg.add_edge(n1.id, n3.id, relation="used_by", weight=1.0)

        re = RecommendationEngine(knowledge_graph=kg)
        recs = re.recommend_related(n1.id)
        assert len(recs) == 2
        assert recs[0].item_type == "knowledge_node"

    def test_recommend_related_no_graph(self):
        """No recommendations when no graph is provided."""
        re = RecommendationEngine()
        recs = re.recommend_related("item-1")
        assert len(recs) == 0

    def test_recommend_trending(self):
        """Trending items are recommended based on interactions."""
        kb = KnowledgeBase()
        item1 = kb.add_item(title="Popular", content="Content", category="cat")
        item2 = kb.add_item(title="Unpopular", content="Content", category="cat")

        re = RecommendationEngine(knowledge_base=kb)
        re.record_interaction("user-1", item1.id)
        re.record_interaction("user-2", item1.id)
        re.record_interaction("user-1", item2.id)

        recs = re.recommend_trending()
        assert len(recs) == 2
        assert recs[0].item_id == item1.id
        assert recs[0].score == 2.0

    def test_recommend_trending_no_kb(self):
        """No trending recommendations when no knowledge base."""
        re = RecommendationEngine()
        recs = re.recommend_trending()
        assert len(recs) == 0

    def test_clear_history(self):
        """User history can be cleared."""
        re = RecommendationEngine()
        re.record_interaction("user-1", "item-1")
        assert len(re.get_user_history("user-1")) == 1
        assert re.clear_history("user-1") is True
        assert len(re.get_user_history("user-1")) == 0

    def test_clear_history_not_found(self):
        """Returns False when clearing non-existent user."""
        re = RecommendationEngine()
        assert re.clear_history("unknown") is False

    def test_recommend_for_user_limit(self):
        """Recommendations respect limit parameter."""
        kb = KnowledgeBase()
        item1 = kb.add_item(title="Item 1", content="Content", category="cat", tags=["python"])
        for i in range(10):
            kb.add_item(title=f"Item {i+2}", content="Content", category="cat", tags=["python"])

        re = RecommendationEngine(knowledge_base=kb)
        re.record_interaction("user-1", item1.id)

        recs = re.recommend_for_user("user-1", limit=3)
        assert len(recs) <= 3
