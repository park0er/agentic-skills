---
name: search-chat-history
description: >-
  Search Codex conversation history for keywords across all sessions and projects.
  Trigger when: user wants to search chat history, find past conversations, recall previous discussions,
  搜索对话历史, 搜对话记录, 找历史对话, 搜一下我们之前聊过的, 之前讨论过, 历史记录搜索,
  search chat history, find old conversation, what did we discuss about X
argument-hint: <keyword> [--context N] [--max N]
allowed-tools:
  - Bash
  - Read
---

# Search Codex Chat History

Search all conversation history stored in `~/.Codex/projects/` for a given keyword and present structured results.

## Workflow

1. **Extract keyword** from user input. The keyword is the main search term the user wants to find in past conversations.

2. **Run the search script:**

```bash
python3 ~/.Codex/skills/search-chat-history/scripts/search_history.py "<keyword>" --context 80 --max 20 --snippets 5
```

Optional flags the user can request:
- `--context N` — characters of context around each match (default 80)
- `--max N` — max sessions to return (default 20)
- `--snippets N` — max snippets per session (default 5)
- `--json` — output raw JSON for further processing

3. **Present results** to the user in a clear format:
   - For each matching session: show the project directory, timestamp, and key context snippets
   - Highlight which messages were from the user vs assistant
   - If the user wants to dive deeper into a specific session, read the full JSONL file at the path shown

4. **Handle edge cases:**
   - No results → suggest alternative keywords or broader terms
   - Too many results → suggest narrowing the search
   - If user wants to read a full conversation, use: `cat ~/.Codex/projects/<project-dir>/<session-id>.jsonl | python3 -c "import sys,json; [print(json.dumps(json.loads(l), ensure_ascii=False)[:500]) for l in sys.stdin if json.loads(l).get('type') in ('user','assistant')]"`

## Example Usage

- `/search-chat-history 元数据管理平台`
- `/search-chat-history nanobot --max 5`
- "搜一下我们之前聊过关于 auth 的对话"
- "我记得之前跟你讨论过 Redis，帮我找一下"
