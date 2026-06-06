c = open("paper_manuscript_zh.md", "r", encoding="utf-8").read()
start = c.find("#### 9.7 与已有理论工作的联系")
end = c.find("#### 9.8 局限性与未来方向")
new = open("tools/novelty_section.txt", "r", encoding="utf-8").read()
c = c[:start] + new + "\n\n" + c[end:]
open("paper_manuscript_zh.md", "w", encoding="utf-8").write(c)
print(f"Done. {len(c)} chars")
