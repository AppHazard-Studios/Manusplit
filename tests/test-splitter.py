"""
Test the document splitter functionality.
"""
import os
import sys
import pytest
from pathlib import Path
import tempfile
import shutil

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from settings import Settings
from splitter import DocumentSplitter
import utils


class TestSplitter:
    """Tests for the DocumentSplitter class."""
    
    @pytest.fixture
    def setup_environment(self):
        """Set up test environment with temporary files and settings."""
        # Create temp dir for output
        output_dir = tempfile.mkdtemp()
        
        # Create test settings
        settings = Settings()
        settings.set("max_words", 50)
        settings.set("output_folder", output_dir)
        settings.set("preserve_formatting", True)
        settings.set("skip_under_limit", False)
        
        # Create a simple test document
        fixtures_dir = Path(os.path.dirname(__file__)) / "fixtures"
        fixtures_dir.mkdir(exist_ok=True)
        
        txt_path = fixtures_dir / "test_doc.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Paragraph one with 5 words.\n\n")
            f.write("Paragraph two has 5 words.\n\n")
            f.write("Paragraph three contains 5 words.\n\n")
            f.write("Paragraph four with 5 words.\n\n")
            f.write("Paragraph five has 5 words.\n\n")
            f.write("Paragraph six contains 5 words.\n\n")
            f.write("Paragraph seven with 5 words.\n\n")
            f.write("Paragraph eight has 5 words.\n\n")
            f.write("Paragraph nine contains 5 words.\n\n")
            f.write("Paragraph ten with 5 words.\n\n")
            
        # Create splitter
        splitter = DocumentSplitter(settings)
        
        # Return everything needed for tests
        yield {
            "settings": settings,
            "splitter": splitter,
            "output_dir": output_dir,
            "txt_path": txt_path
        }
        
        # Clean up
        try:
            shutil.rmtree(output_dir)
            shutil.rmtree(fixtures_dir)
        except:
            pass
    
    def test_word_counting(self):
        """Test word counting functionality."""
        text = "This is a test with 7 words."
        assert utils.count_words(text) == 7
        
        text = ""
        assert utils.count_words(text) == 0
        
        text = "One"
        assert utils.count_words(text) == 1
    
    def test_txt_splitting(self, setup_environment):
        """Test splitting a text file."""
        env = setup_environment
        
        # Process the test file
        result = env["splitter"].process_file(env["txt_path"])
        
        # Check results
        assert result["success"] is True
        assert result["total_words"] == 50  # 10 paragraphs × 5 words
        assert result["parts_created"] > 1
        
        # Check output files exist
        for output_file in result["output_files"]:
            assert os.path.exists(output_file)
            
        # Check content distribution
        total_words_in_parts = 0
        for output_file in result["output_files"]:
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
                words = utils.count_words(content)
                total_words_in_parts += words
                
                # Each part should have at most max_words
                assert words <= env["settings"].get("max_words")
                
        # Total words across all parts should match original
        assert total_words_in_parts == 50
    
    def test_skip_under_limit(self, setup_environment):
        """Test skipping files under the word limit."""
        env = setup_environment
        
        # Update settings to skip files under limit
        env["settings"].set("max_words", 100)
        env["settings"].set("skip_under_limit", True)
        
        # Process the test file
        result = env["splitter"].process_file(env["txt_path"])
        
        # Check results - file should be skipped
        assert result["success"] is True
        assert result["total_words"] == 50
        assert result["parts_created"] == 0
        assert len(result["output_files"]) == 0
    
    def test_paragraph_boundary(self, setup_environment):
        """Test that splits occur at paragraph boundaries."""
        env = setup_environment
        
        # Set max words to 22 (between 4-5 paragraphs)
        env["settings"].set("max_words", 22)
        
        # Process the test file
        result = env["splitter"].process_file(env["txt_path"])
        
        # Check results
        assert result["success"] is True
        assert result["parts_created"] > 1
        
        # Check content of first part - should have complete paragraphs
        with open(result["output_files"][0], "r", encoding="utf-8") as f:
            content = f.read()
            
            # Count paragraphs
            paragraphs = [p for p in content.split("\n\n") if p.strip()]
            
            # Each paragraph should be complete (5 words)
            for para in paragraphs:
                assert utils.count_words(para) == 5
            
            # First file should have max 4 complete paragraphs (20 words)
            assert len(paragraphs) <= 4
