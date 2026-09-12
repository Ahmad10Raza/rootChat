import re

def parse_markdown_blocks(text: str):
    """
    Parses text and yields a sequence of tuples: (is_code: bool, content: str, language: str)
    This allows creating separate UI widgets for text vs code blocks.
    """
    code_block_pattern = re.compile(r"```(.*?)\n(.*?)```", re.DOTALL)
    last_end = 0
    for match in code_block_pattern.finditer(text):
        start, end = match.span()
        if start > last_end:
            yield (False, text[last_end:start].strip(), "")
            
        language = match.group(1).strip()
        code = match.group(2).strip()
        yield (True, code, language)
        last_end = end
        
    if last_end < len(text):
        yield (False, text[last_end:].strip(), "")
