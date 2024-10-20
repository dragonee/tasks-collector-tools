# Tasks Collector Tools

These tools add CLI support to the [Tasks Collector](https://github.com/dragonee/tasks-collector) application.

## All-in-one

### tasks (1.0.2)

```
Connect to the Tasks Collector.

Usage: 
    tasks [options]

Options:
    --thread THREAD  Use specific thread [default: Inbox].
    -h, --help       Show this message.
    --version        Show version information.

By default, tasks are added to the "Inbox" thread.
By prefixing a line with `!` or `#`, it will be added to the Habit Tracker instead.

Available commands:
  observation
  olist
  habits
  hlist
  oedit
  edit
  quest
  journal
  update
  help
  clear

Quit by pressing Ctrl+D or Ctrl+C.
```

## Journalling

### journal (1.1)

```
Add journal entry.

Usage: 
    journal [options]

Options:
    -s               Also save a copy as new observation, filling Situation field.
    -o               Alias for -s.
    -t THREAD, --thread THREAD  Use this thread [default: Daily]
    -h, --help       Show this message.
    --version        Show version information.
```

## Observations

### observation (1.0.2)

```
Add an observation.

Usage: 
    observation [options]

Options:
    -l, --list       List last couple of observations.
    -n, --number N   With -l, show N observations [default: 20].
    -c, --chars N    With -l, show N chars of the situation [default: 100].
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

## Habits

### habits (1.1)

```
Track habits daily or list them.

Usage: 
    habits [options]

Options:
    --yesterday      Set the date to yesterday.
    -l, --list       List habits
    -o, --output FILENAME  If listing, output to file [default: -]
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

### observationdump (1.1)

```
Dump observations to markdown files.

Usage: 
    observationdump [options] PATH

Options:
    -d DATE_FROM, --from FROM  Dump from specific date.
    -D DATE_TO, --to DATE_TO   Dump to specific date.
    -f, --force      Overwrite existing files.
    --stream ID      Dump object with specific Event Stream ID.
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

