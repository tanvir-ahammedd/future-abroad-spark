import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"C:\Users\tanvir\.gemini\antigravity-ide\brain\5ccbee44-ab3b-4c5d-9a56-a9544bbef8ae\.system_generated\tasks\task-245.log", "r", encoding="utf-8") as f:
    content = f.read()

start_idx = content.find("Response text:")
end_idx = content.find("Grounding Metadata:")
if start_idx != -1:
    print(content[start_idx:end_idx].encode("utf-8", errors="replace").decode("utf-8"))
else:
    print("Response text block not found")
