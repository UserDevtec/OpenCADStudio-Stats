# OpenCADStudio realtime download growth

Tracks GitHub Release asset downloads for:

`HakanSeven12/OpenCADStudio`

The workflow runs every 5 minutes and builds a growing cumulative line graph.

## Generated graphs

```text
stats/download-growth-24h.svg
stats/download-growth-7d.svg
stats/download-growth-30d.svg
```

It also generates:

```text
stats/downloads.json
stats/download-history.json
stats/downloads-today.json
stats/downloads-hour.json
stats/downloads-week.json
stats/downloads-latest-release.json
stats/downloads-total.json
```

## Install

Upload all files to the root of your own GitHub repository.

Then go to:

**Settings > Actions > General > Workflow permissions**

Choose:

**Read and write permissions**

Save it.

Then run:

**Actions > Update OpenCADStudio download growth > Run workflow**

The first execution is the baseline. After the next measurements, the line begins to grow.

## Put the line graph in your README

Replace `YOUR_GITHUB_USERNAME` and `YOUR_REPOSITORY`.

### Last 24 hours

```md
![OpenCADStudio download growth](https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/main/stats/download-growth-24h.svg)
```

### Last 7 days

```md
![OpenCADStudio 7 day download growth](https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/main/stats/download-growth-7d.svg)
```

### Last 30 days

```md
![OpenCADStudio 30 day download growth](https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/main/stats/download-growth-30d.svg)
```

## Badges

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

## Refresh rate

The workflow targets one measurement every 5 minutes.

The history file keeps the last 30 days, which is about 8,640 measurements at that interval.

## Change repository

Edit:

```text
.github/workflows/update-download-stats.yml
```

and change:

```yaml
env:
  TARGET_REPO: HakanSeven12/OpenCADStudio
  TARGET_TIMEZONE: Europe/Amsterdam
```
