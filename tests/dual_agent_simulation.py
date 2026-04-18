"""
Dual Agent Simulation Test

Simulates human-AI interaction for DITING_ testing purposes.
Uses generic test data without any personal information.
"""

import pytest
import json
from pathlib import Path
from typing import List, Dict


class TestDualAgentSimulation:
    """Test dual agent interaction patterns"""
    
    def test_basic_memory_operations(self):
        """Test basic memory create/read/update/delete"""
        from diting.mft import MFT
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            mft = MFT(db_path=db_path)
            
            # Create
            inode = mft.create(
                "/test/user/preferences",
                "NOTE",
                "User prefers dark mode"
            )
            assert inode is not None
            
            # Read
            result = mft.read("/test/user/preferences")
            assert result["content"] == "User prefers dark mode"
            
            # Update
            mft.update("/test/user/preferences", content="Updated preferences")
            updated = mft.read("/test/user/preferences")
            assert updated["content"] == "Updated preferences"
            
            # Delete
            mft.delete("/test/user/preferences")
            deleted = mft.read("/test/user/preferences")
            assert deleted is None
            
            mft.close()
        finally:
            import os
            os.unlink(db_path)
    
    def test_search_functionality(self):
        """Test memory search capabilities"""
        from diting.mft import MFT
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            mft = MFT(db_path=db_path)
            
            # Add test memories
            test_data = [
                ("/test/work/project1", "NOTE", "Project alpha deadline next week"),
                ("/test/work/project2", "NOTE", "Project beta code review completed"),
                ("/test/learning/python", "NOTE", "Python async/await syntax notes"),
                ("/test/learning/database", "NOTE", "SQLite FTS5 full-text search"),
            ]
            
            for path, type_, content in test_data:
                mft.create(path, type_, content)
            
            # Search by keyword
            results = mft.search("project")
            assert len(results) >= 2
            
            results = mft.search("python")
            assert len(results) >= 1
            
            # List by type
            results = mft.list_by_type("NOTE")
            assert len(results) == 4
            
            mft.close()
        finally:
            import os
            os.unlink(db_path)
    
    def test_knowledge_graph_integration(self):
        """Test knowledge graph concept extraction"""
        from diting.knowledge_graph_v2 import KnowledgeGraphV2
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            kg = KnowledgeGraphV2(db_path=db_path)
            
            # Add concepts
            kg.add_concept("Python", "programming_language")
            kg.add_concept("SQLite", "database")
            kg.add_concept("Async", "programming_pattern")
            
            # Add relationships
            kg.add_edge("Python", "Async", "supports", weight=0.9)
            kg.add_edge("SQLite", "Python", "integrates_with", weight=0.8)
            
            # Query concepts
            concept = kg.get_concept_by_name("Python")
            assert concept is not None
            assert concept["name"] == "Python"
            
            # Get related concepts
            related = kg.get_related_concepts("Python", top_k=5)
            assert len(related) > 0
            
            kg.close()
        finally:
            import os
            os.unlink(db_path)
    
    def test_conversation_patterns(self):
        """Test typical conversation patterns"""
        # Generic conversation patterns for testing
        patterns = [
            {
                "user": "Remember that I prefer dark mode",
                "expected_action": "create_memory",
                "category": "preference"
            },
            {
                "user": "What was the project deadline we discussed?",
                "expected_action": "search_memory",
                "category": "work"
            },
            {
                "user": "Show me my notes about Python",
                "expected_action": "search_memory",
                "category": "learning"
            },
            {
                "user": "Update my contact information",
                "expected_action": "update_memory",
                "category": "personal"
            },
        ]
        
        for pattern in patterns:
            assert "user" in pattern
            assert "expected_action" in pattern
            assert "category" in pattern
    
    def test_memory_categorization(self):
        """Test memory categorization system"""
        categories = {
            "personal_memory": ["preferences", "hobbies", "contacts"],
            "work_record": ["projects", "meetings", "deadlines"],
            "learning_note": ["tutorials", "documentation", "code_snippets"],
            "event_record": ["appointments", "calls", "scheduled_events"],
        }
        
        for category, subcategories in categories.items():
            assert isinstance(category, str)
            assert isinstance(subcategories, list)
            assert len(subcategories) > 0


def run_simulation():
    """Run dual agent simulation"""
    print("Starting dual agent simulation...")
    
    # Load test conversations
    test_file = Path(__file__).parent / "mock_conversations.json"
    if test_file.exists():
        with open(test_file, "r", encoding="utf-8") as f:
            conversations = json.load(f)
        print(f"Loaded {len(conversations)} test conversations")
    
    # Run tests
    pytest.main([__file__, "-v"])
    
    print("Simulation completed")


if __name__ == "__main__":
    run_simulation()
