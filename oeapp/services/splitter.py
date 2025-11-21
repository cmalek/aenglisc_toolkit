"""Sentence and token splitter service."""

import re


def split_sentences(text: str) -> list[str]:  # noqa: PLR0912
    """
    Split text into sentences.

    Args:
        text: Input Old English text

    Returns:
        List of sentence strings

    """
    if not text.strip():
        return []

    sentences: list[str] = []
    current_sentence = ""
    i = 0
    inside_quotes = False
    quote_char = None

    while i < len(text):
        char = text[i]

        # Track quote state
        if char in ('"', "'"):
            if not inside_quotes:
                # Opening quote
                inside_quotes = True
                quote_char = char
                current_sentence += char
            elif char == quote_char:
                # Closing quote
                inside_quotes = False
                quote_char = None
                current_sentence += char
                # Check if we should split after closing quote
                # Split if the quote contains sentence-ending punctuation (.!?)
                # before the closing quote
                # Check if the character immediately before the closing quote is
                # sentence-ending punctuation
                min_length_for_preceding_char = 2
                char_before_closing_quote = None
                if len(current_sentence) >= min_length_for_preceding_char:
                    # Look at the character before the closing quote
                    char_before_closing_quote = current_sentence[-2]

                j = i + 1
                # Skip whitespace
                while j < len(text) and text[j].isspace():
                    j += 1

                # Split if:
                # 1. Quote contains sentence-ending punctuation (.!?) before
                #    closing quote AND followed by uppercase letter
                # 2. Or followed by [number] marker (always split on these)
                should_split_after_quote = False
                if j < len(text):
                    if (
                        text[j] == "[" and j + 1 < len(text) and text[j + 1].isdigit()
                    ) or (
                        char_before_closing_quote in (".", "!", "?")
                        and text[j].isupper()
                    ):
                        should_split_after_quote = True

                if should_split_after_quote:
                    # End of sentence - save it
                    sentence = current_sentence.strip()
                    if sentence:
                        sentences.append(sentence)
                    current_sentence = ""
                    # Skip the whitespace we looked ahead
                    i = j - 1
            else:
                # Different quote type inside quotes - treat as regular char
                current_sentence += char
        elif char in (".", "!", "?"):
            current_sentence += char
            # Only split if we're not inside quotes
            if not inside_quotes:
                # Check if this is followed by whitespace or end of text
                # Look ahead to see if there's content after optional whitespace
                j = i + 1
                # Skip whitespace
                while j < len(text) and text[j].isspace():
                    j += 1
                # Split if: end of text, uppercase (new sentence),
                # quote (new quoted sentence), or [ followed by digit (like [1])
                # Don't split if lowercase (likely abbreviation)
                should_split = (
                    j >= len(text)
                    or text[j].isupper()
                    or text[j] in ('"', "'")
                    or (text[j] == "[" and j + 1 < len(text) and text[j + 1].isdigit())
                )

                if should_split:
                    # End of sentence - save it
                    sentence = current_sentence.strip()
                    if sentence:
                        sentences.append(sentence)
                    current_sentence = ""
                    # Skip the whitespace we looked ahead
                    i = j - 1
        elif char == "[" and i + 1 < len(text) and text[i + 1].isdigit():
            # Handle [number] markers - skip the entire marker
            # Find the closing ]
            j = i + 1
            while j < len(text) and text[j].isdigit():
                j += 1
            if j < len(text) and text[j] == "]":
                # Skip the entire [number] marker
                i = j  # Will be incremented at end of loop
            else:
                # Not a valid [number] marker, treat as regular char
                current_sentence += char
        else:
            current_sentence += char

        i += 1

    # Add the last sentence if there's any content
    if current_sentence.strip():
        sentences.append(current_sentence.strip())

    # Remove any [numbers] from the sentences
    result = [re.sub(r"\[\d+\]", "", s) for s in sentences]
    # Also remove any remaining number] patterns (in case [ was removed but number] remains)
    result = [re.sub(r"^\d+\]\s*", "", s) for s in result]
    # If a sentence is just a number in [brackets], remove it
    result = [s for s in result if not re.match(r"^\[\d+\]\s*$", s.strip())]
    # Filter out empty strings and strip leading/trailing whitespace
    return [s.strip() for s in result if s.strip()]
