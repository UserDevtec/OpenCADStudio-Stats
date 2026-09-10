# OpenCADStudio download badges

This small GitHub Actions setup tracks GitHub Release downloads for:

`HakanSeven12/OpenCADStudio`

It stores snapshots in your own repository and generates Shields.io endpoint files.

## Files

```text
.github/workflows/update-download-stats.yml
scripts/update_download_stats.py
stats/download-history.json
stats/downloads.json
stats/downloads-today.json
stats/downloads-hour.json
stats/downloads-week.json
stats/downloads-latest-release.json
stats/downloads-total.json
```

## Install

Copy the contents of this package into the root of your own GitHub repository and push it.

Then open:

**GitHub > Actions > Update OpenCADStudio download badges > Run workflow**

After the first run, the `stats` files will be created/updated automatically.

The workflow also runs every 5 minutes.

## Important repository setting

The workflow needs permission to commit updated statistics.

Open:

**Settings > Actions > General > Workflow permissions**

Select:

**Read and write permissions**

Then save.

## README badges

Replace `YOUR_GITHUB_USERNAME/YOUR_REPOSITORY` below with the repository where you installed these files.

### Downloads today

```md
![Downloads today](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/main/stats/downloads-today.json)
```

### Downloads last hour

```md
![Downloads last hour](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/main/stats/downloads-hour.json)
```

### Downloads last 7 days

```md
![Downloads last 7 days](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/main/stats/downloads-week.json)
```

### Latest release downloads

```md
![Latest release downloads](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/main/stats/downloads-latest-release.json)
```

### Total downloads

```md
![Total downloads](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/main/stats/downloads-total.json)
```

## Example

After the Action has collected data for a while you can show badges like:

```text
downloads today | 1.2k
downloads last hour | 83
downloads last 7 days | 8.7k
latest release downloads | 11.6k
total downloads | 85.3k
```

## Change the tracked repository

Edit:

`.github/workflows/update-download-stats.yml`

Change:

```yaml
env:
  TARGET_REPO: HakanSeven12/OpenCADStudio
  TARGET_TIMEZONE: Europe/Amsterdam
```

For example:

```yaml
env:
  TARGET_REPO: owner/repository
  TARGET_TIMEZONE: Europe/Amsterdam
```

## Notes

GitHub Actions scheduled jobs are not guaranteed to start at the exact scheduled second. GitHub may delay scheduled workflows during busy periods.

The first run creates a baseline. Therefore "today", "last hour", and "last 7 days" become useful only after historical measurements have been collected.

GitHub Release asset download counters are cumulative. This workflow calculates period statistics by comparing the current counter with earlier snapshots.
