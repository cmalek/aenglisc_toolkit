
import pytest
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCursor, QTextCharFormat

def test_qtextcursor_charformat_behavior(qapp):
    te = QTextEdit()
    doc = te.document()
    cursor = QTextCursor(doc)

    fmt1 = QTextCharFormat()
    fmt1.setProperty(1000, "prop1")
    cursor.insertText("word1", fmt1)

    fmt_space = QTextCharFormat() # No property
    cursor.insertText(" ", fmt_space)

    fmt2 = QTextCharFormat()
    fmt2.setProperty(1000, "prop2")
    cursor.insertText("word2", fmt2)

    # Text is "word1 word2"
    # word1: 0-5
    # space: 5-6
    # word2: 6-11

    # Check start of word2 (position 6)
    cursor.setPosition(6)
    fmt = cursor.charFormat()
    print(f"\nPos 6 (start of word2): hasProperty={fmt.hasProperty(1000)}, value={fmt.property(1000)}")
    # Expected: hasProperty=False (because it gives format of char at 5, the space)

    # Check middle of word2 (position 7)
    cursor.setPosition(7)
    fmt = cursor.charFormat()
    print(f"Pos 7 (middle of word2): hasProperty={fmt.hasProperty(1000)}, value={fmt.property(1000)}")
    # Expected: hasProperty=True, value="prop2"

    # Check start of word1 (position 0)
    cursor.setPosition(0)
    fmt = cursor.charFormat()
    print(f"Pos 0 (start of word1): hasProperty={fmt.hasProperty(1000)}, value={fmt.property(1000)}")
    # Expected: hasProperty=False (or whatever is at -1?)

