"""
Debug: check figure reference matching in the markdown
"""
with open("paper_manuscript_zh.md", "r", encoding="utf-8") as f:
    content = f.read()

# Extract a paragraph with figure references
lines = content.split("\n")
for i, line in enumerate(lines):
    if "\u56fe 1" in line:  # 图 1
        print(f"Line {i}: {repr(line[:120])}")
        break

# Test clean_text
import re
test = "\u56fe 1 \u548c\u56fe 2 \u5c06\u56db\u6848\u4f8b\u7684\u89c2\u6d4b\u9000\u5316\u4e0e\u53ef\u9760\u6027\u54cd\u5e94\u653e\u5728\u540c\u4e00\u8bc1\u636e\u94fe\u4e2d\u3002"
cleaned = test
cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)
cleaned = re.sub(r'\*(.+?)\*', r'\1', cleaned)
cleaned = re.sub(r'\$(.+?)\$', r'\1', cleaned)
cleaned = re.sub(r'`([^`]+?)`', r'\1', cleaned)
print(f"\nCleaned: {repr(cleaned)}")

# Check if figure keys match
for key in ["\u56fe 1", "\u56fe 2", "\u56fe 3", "\u56fe 4"]:
    print(f"'{key}' in cleaned: {key in cleaned}")

# Check the actual FIGURES dict keys vs content
fig_names = ["\u56fe 1", "\u56fe 2", "\u56fe 3", "\u56fe 4", "\u56fe 5", "\u56fe 6"]
for fn in fig_names:
    idx = content.find(fn)
    if idx >= 0:
        print(f"Found '{fn}' at pos {idx}")
    else:
        print(f"NOT found '{fn}'")
