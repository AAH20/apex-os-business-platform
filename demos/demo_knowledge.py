#!/usr/bin/env python3
"""Demo: Knowledge Graph operations in APEX-OS Business Platform.

Demonstrates:
1. Create knowledge graph
2. Add entity
3. Query graph
4. Get recommendations
5. Learn (update graph from new information)
"""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from apex_os.knowledge import KnowledgeGraph, Entity, Relation


def demo_create_graph():
    """1. Create a new knowledge graph."""
    print("=" * 60)
    print("DEMO 1: Create Knowledge Graph")
    print("=" * 60)

    graph = KnowledgeGraph(name="business_kb")
    print(f"Created graph: {graph.name}")
    print(f"Graph ID: {graph.id}")
    print(f"Initial entity count: {graph.entity_count}")
    print(f"Initial relation count: {graph.relation_count}")
    print()
    return graph


def demo_add_entity(graph):
    """2. Add entities and relations to the graph."""
    print("=" * 60)
    print("DEMO 2: Add Entity")
    print("=" * 60)

    # Add entities
    alice = Entity(id="emp_001", type="Person", name="Alice", 
                   attributes={"role": "Engineer", "dept": "Platform"})
    bob = Entity(id="emp_002", type="Person", name="Bob",
                 attributes={"role": "Manager", "dept": "Platform"})
    project_x = Entity(id="proj_001", type="Project", name="Project X",
                       attributes={"status": "active", "priority": "high"})

    graph.add_entity(alice)
    graph.add_entity(bob)
    graph.add_entity(project_x)

    print(f"Added entity: {alice.name} (type={alice.type}, id={alice.id})")
    print(f"Added entity: {bob.name} (type={bob.type}, id={bob.id})")
    print(f"Added entity: {project_x.name} (type={project_x.type}, id={project_x.id})")

    # Add relations
    graph.add_relationship("emp_001", "works_on", "proj_001")
    graph.add_relationship("emp_002", "manages", "emp_001")
    graph.add_relationship("emp_002", "works_on", "proj_001")

    print(f"\nAdded relationships:")
    print(f"  emp_001 --[works_on]--> proj_001")
    print(f"  emp_002 --[manages]--> emp_001")
    print(f"  emp_002 --[works_on]--> proj_001")
    print(f"\nTotal entities: {graph.entity_count}")
    print(f"Total relations: {graph.relation_count}")
    print()
    return graph


def demo_query_graph(graph):
    """3. Query the knowledge graph."""
    print("=" * 60)
    print("DEMO 3: Query Graph")
    print("=" * 60)

    # Query by entity type
    people = graph.query(entity_type="Person")
    print(f"Query: entity_type='Person' -> {len(people)} results")
    for p in people:
        print(f"  - {p.name} ({p.id})")

    # Query by relationship
    works_on = graph.query(relation="works_on")
    print(f"\nQuery: relation='works_on' -> {len(works_on)} results")
    for src, rel, tgt in works_on:
        print(f"  - {src} --[{rel}]--> {tgt}")

    # Query neighbors
    neighbors = graph.get_neighbors("emp_001")
    print(f"\nQuery: neighbors of 'emp_001' -> {len(neighbors)} results")
    for n in neighbors:
        print(f"  - {n.name} ({n.type})")

    # SPARQL-like query
    results = graph.query_pattern(
        subject_type="Person",
        relation="works_on",
        object_type="Project"
    )
    print(f"\nQuery: Person -[works_on]-> Project -> {len(results)} results")
    for r in results:
        print(f"  - {r['subject']} works on {r['object']}")
    print()
    return graph


def demo_recommendations(graph):
    """4. Get recommendations from the graph."""
    print("=" * 60)
    print("DEMO 4: Get Recommendations")
    print("=" * 60)

    # Recommend collaborators for a person
    recs = graph.recommend_collaborators("emp_001", limit=3)
    print(f"Recommended collaborators for Alice (emp_001):")
    for rec in recs:
        print(f"  - {rec['name']} (score={rec['score']:.2f}, reason={rec['reason']})")

    # Recommend projects for a person
    proj_recs = graph.recommend_projects("emp_002", limit=3)
    print(f"\nRecommended projects for Bob (emp_002):")
    for rec in proj_recs:
        print(f"  - {rec['name']} (score={rec['score']:.2f})")

    # Find similar entities
    similar = graph.find_similar("proj_001", limit=3)
    print(f"\nEntities similar to Project X:")
    for s in similar:
        print(f"  - {s['name']} (similarity={s['score']:.2f})")
    print()
    return graph


def demo_learn(graph):
    """5. Learn — update graph from new information."""
    print("=" * 60)
    print("DEMO 5: Learn (Update Graph)")
    print("=" * 60)

    # Learn a new fact
    new_entity = Entity(id="proj_002", type="Project", name="Project Y",
                        attributes={"status": "planning", "priority": "medium"})
    graph.add_entity(new_entity)
    graph.add_relationship("emp_001", "works_on", "proj_002")
    print(f"Learned: Alice now also works on Project Y")

    # Learn from observation — infer a new relation
    inferred = graph.infer_relations("emp_001")
    print(f"\nInferred relations for Alice:")
    for rel in inferred:
        print(f"  - {rel['subject']} --[{rel['relation']}]--> {rel['object']}")

    # Update entity attributes
    graph.update_entity("proj_001", {"status": "completed", "progress": 100})
    updated = graph.get_entity("proj_001")
    print(f"\nUpdated Project X attributes: {updated.attributes}")

    # Learn from feedback
    graph.learn_from_feedback(
        subject="emp_001",
        relation="works_on",
        object="proj_001",
        feedback="positive"
    )
    print(f"\nRecorded positive feedback: Alice works_on Project X")

    print(f"\nFinal graph stats:")
    print(f"  Entities: {graph.entity_count}")
    print(f"  Relations: {graph.relation_count}")
    print(f"  Facts learned: {graph.facts_learned}")
    print()
    return graph


def main():
    """Run all knowledge graph demos."""
    print("\n" + "#" * 60)
    print("# APEX-OS Knowledge Graph Demo")
    print("#" * 60 + "\n")

    graph = demo_create_graph()
    graph = demo_add_entity(graph)
    graph = demo_query_graph(graph)
    graph = demo_recommendations(graph)
    graph = demo_learn(graph)

    print("=" * 60)
    print("All demos completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
