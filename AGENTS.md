# Personal Wiki Agent Instructions

You maintain a local Markdown-based Personal Wiki.

## Main Goal

Convert information from the `raw/` folder into clean, useful, interconnected Markdown notes.

The wiki should work well in Obsidian.

## Folder Structure

* `raw/` contains original source files.
* `wiki/` contains organized Markdown knowledge notes.
* `wiki/index.md` is the main knowledge index.
* `logs/ingestion_log.md` records processing activity.

## Processing Rules

When processing files from `raw/`:

1. Read the source carefully.
2. Extract only important and durable information.
3. Identify important:

   * concepts
   * facts
   * tools
   * technologies
   * people
   * projects
   * relationships
4. Remove unnecessary repetition and filler.
5. Do not invent information.
6. Preserve useful technical details.
7. Keep notes concise but informative.

## Note Creation Rules

Before creating a note:

1. Check whether a related note already exists in `wiki/`.
2. If the topic already exists, update that note.
3. Create a new note only when the concept is genuinely new.
4. Avoid duplicate notes.

Do not create files such as:

* rag-copy.md
* rag-new.md
* machine-learning-2.md

unless they represent genuinely different concepts.

## Linking Rules

Use Obsidian-style internal links:

[[Concept Name]]

Example:

[[Machine Learning]]

[[Embeddings]]

[[PostgreSQL]]

[[Model Context Protocol]]

Add internal links whenever two concepts are meaningfully related.

## Note Format

Each note should use this structure:

# Title

Short explanation of the topic.

## Key Points

* Important point
* Important point
* Important point

## Related Topics

* [[Related Topic]]
* [[Another Topic]]

## Sources

* raw/source_filename

## Index Maintenance

Maintain:

`wiki/index.md`

The index should:

* contain links to important wiki notes
* group related topics where possible
* remain easy to navigate
* use [[Internal Links]]

## Logging

Maintain:

`logs/ingestion_log.md`

For every processed source record:

* source filename
* date processed
* notes created
* notes updated
* important links added

## Raw File Safety

Never modify or delete files inside `raw/`.

The `raw/` folder is the permanent source material.

## Answering Questions

When answering questions from this knowledge base:

1. Start with `wiki/index.md`.
2. Find relevant notes.
3. Follow useful [[Internal Links]].
4. Read only the files needed.
5. Base answers on information present in the wiki.
6. Mention which wiki notes were used.
7. If the answer is not present in the wiki, clearly say so.

## Obsidian Compatibility

All Markdown files must remain compatible with Obsidian.

Use:

[[Internal Links]]

so Obsidian Graph View can visualize relationships between notes.
