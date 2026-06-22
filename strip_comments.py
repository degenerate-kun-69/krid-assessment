import os
import tokenize

def strip_comments_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    with open(filepath, 'rb') as f:
        tokens = list(tokenize.tokenize(f.readline))
    
    # We want to reconstruct the file but omit tokens of type tokenize.COMMENT
    # tokenize untokenize is tricky to get exact spacing right, 
    # but we can also just do line-by-line or token-by-token replacement.
    
    # Actually, a simpler way without breaking formatting:
    # Just iterate through tokens. If it's a COMMENT, replace that exact byte range in the source with spaces or just remove it.
    
    # Let's do it carefully:
    # We will build the output string by keeping everything except COMMENT tokens.
    
    # Using untokenize:
    # The output of untokenize(filtered_tokens) might change whitespace.
    # A better approach: 
    
    out = []
    last_lineno = -1
    last_col = 0
    
    with open(filepath, 'rb') as f:
        for tok in tokenize.tokenize(f.readline):
            token_type = tok.type
            token_string = tok.string
            start_line, start_col = tok.start
            end_line, end_col = tok.end
            
            if token_type == tokenize.ENCODING:
                continue
                
            if last_lineno != start_line:
                last_col = 0
            
            if start_col > last_col:
                out.append(" " * (start_col - last_col))
                
            if token_type == tokenize.COMMENT:
                # Omit the comment string.
                # However, to avoid leaving trailing spaces before the newline, we can just not append anything
                pass
            else:
                out.append(token_string)
                
            last_lineno = end_line
            last_col = end_col

    # Join the output
    result = "".join(out)
    
    # Clean up empty lines that were just comments
    cleaned_lines = []
    for line in result.split('\n'):
        if line.strip() == '' and line != '':
            # If line is only whitespace, but we don't want to remove all empty lines,
            # we just keep empty lines as they were. 
            pass
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result)

def main():
    for root, dirs, files in os.walk('.'):
        if '.venv' in root or '__pycache__' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if filepath.endswith('strip_comments.py'):
                    continue
                try:
                    strip_comments_from_file(filepath)
                    print(f"Stripped: {filepath}")
                except Exception as e:
                    print(f"Failed {filepath}: {e}")

if __name__ == '__main__':
    main()
