# Tasks Collector Tools

These tools add CLI support to the [Tasks Collector](https://github.com/dragonee/tasks-collector) application.

## Journalling

### journal (1.1)

```
Add journal entry.

Usage: 
    journal [options]

Options:
    -o               Also save a copy as observation.
    -t THREAD, --thread THREAD  Use this thread [default: Daily]
    -h, --help       Show this message.
    --version        Show version information.
```

## Observations

### observation (1.0.1)

```
Add an observation.

Usage: 
    observation [options]

Options:
    -l, --list       List last couple of observations.
    --date DATE      Use specific date.
    -s, --save       Save as default for updates [default: False].
    --thread THREAD  Use specific thread [default: big-picture].
    --type TYPE      Choose type [default: observation].
    -h, --help       Show this message.
    --version        Show version information.
```

### update (1.0.2)

```
Add update to an observation.

Usage: 
    update [options] [ID]

Options:
    -h, --help       Show this message.
    --version        Show version information.
```

## Task management

### addtask (1.0.3)

```
Add a task.

Usage: 
    addtask [options] [TEXT]

Options:
    --thread THREAD  Use specific thread [default: Inbox].
    -h, --help       Show this message.
    --version        Show version information.
```

## Quests

### quest (1.0.1)

```
Follow a quest.

Usage: 
    quest [options] KEY [STAGE]

Options:
    -h, --help       Show this message.
    --version        Show version information.
```

## Tools for periodical reflections

TODO: write up process on how to do a periodical reflection.

### observationdump (1.0.3)

```
Dump observations to markdown files.

Usage: 
    observationdump [options] PATH

Options:
    -d DATE_FROM, --from FROM  Dump from specific date.
    -D DATE_TO, --to DATE_TO   Dump to specific date.
    -f, --force      Overwrite existing files.
    --pk ID          Dump object with specific ID.
    --year YEAR      Dump specific year.
    -h, --help       Show this message.
    --version        Show version information.
```

### boardmd (1.0)

```
Dump a board to markdown.

Usage: 
    boardmd [options]

Options:
    --thread THREAD  Use specific thread [default: big-picture].
    --enumerate      Add numberic enumeration to points (e.g. 1.2.4.)
    -h, --help       Show this message.
    --version        Show version information.
```
