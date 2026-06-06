c = open("paper_manuscript_zh.md", "r", encoding="utf-8").read()
start = c.find("### 9. 讨论")
end = c.find("### 10. 结论")

new_disc = open("tools/discussion_rewrite.txt", "r", encoding="utf-8").read()

c = c[:start] + new_disc + c[end:]
open("paper_manuscript_zh.md", "w", encoding="utf-8").write(c)
print(f"Done. {len(c)} chars")
