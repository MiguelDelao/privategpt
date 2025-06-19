# Logging Coverage Checklist

Mark each item with [x] when implemented.

## HTTP layer
- [ ] `http.request.start` (method, path)
- [ ] `http.request.end` (status, duration_ms)

## Core commands / queries
- [ ] `command.ingest_document.start`
- [ ] `command.ingest_document.complete`
- [ ] `query.answer_question.start`
- [ ] `query.answer_question.complete`

## Adapters
- [ ] `chunk.embed` (adapter, batch)
- [ ] `vector.add` (adapter, count)
- [ ] `vector.search` (adapter, top_k)
- [ ] `task.enqueue` (task, task_id)

## Errors
- [ ] Exceptions logged at level=error with stack info and `event=exception`

Update this file in the PR that introduces each logging statement. 