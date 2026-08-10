# KVDO wedstrijden — auto-updating calendar feeds

Self-hosted `.ics` calendar feeds of **KV Oostende Diksmuide league games**,
scraped daily from <https://kv-do.be/kalender/> and served straight from this repo.
Two separate calendars: **home** games and **away** games. Cup games are excluded.
100% free — runs on GitHub Actions, no server, no paid services.

## How it works

1. `scrape.py` fetches the club calendar page, parses the scheduled matches,
   keeps only **league** games, and splits them into **home** and **away**.
2. A GitHub Action (`.github/workflows/update-feed.yml`) runs it once a day,
   regenerates both `.ics` files, and commits them back if anything changed.
3. Your calendar app subscribes to the raw file URLs and re-checks them
   periodically, so date changes on the website flow through automatically.

## One-time setup

1. Create a **new public repository** on your GitHub account (e.g. `kvdo-feed`).
2. Upload these files, keeping the folder structure:
   - `scrape.py`
   - `kvdo-thuis.ics`  (seed home feed — works before the first scheduled run)
   - `kvdo-uit.ics`    (seed away feed)
   - `.github/workflows/update-feed.yml`
   - `README.md`
3. Go to **Settings → Actions → General**, scroll to **Workflow permissions**,
   select **Read and write permissions**, and save. (Lets the action commit.)
4. Open the **Actions** tab, pick *"Update KVDO calendar feeds"*, and click
   **Run workflow** once to confirm. You should see a new commit.

## Subscribe to the feeds

Replace `<YOUR-USERNAME>` in these URLs:

```
Home games: https://raw.githubusercontent.com/<YOUR-USERNAME>/kvdo-feed/main/kvdo-thuis.ics
Away games: https://raw.githubusercontent.com/<YOUR-USERNAME>/kvdo-feed/main/kvdo-uit.ics
```

Add each as a **subscription** (not a one-time import). Subscribe to one or both:

- **Google Calendar** → Other calendars → **From URL** → paste a URL.
  (Google refreshes external feeds on its own schedule, often every 8–24h.)
- **Apple Calendar** → File → **New Calendar Subscription** → paste a URL.
  You can set auto-refresh to hourly/daily.
- **Outlook** → Add calendar → **Subscribe from web** → paste a URL.

Tip: swapping `https://` for `webcal://` forces some apps into subscribe mode.

## Adjusting

- **Change frequency:** edit the `cron:` line in the workflow.
- **Include cup games:** remove the `is_league(m)` filter in `main()`.
- **One combined calendar instead of two:** in `main()`, call `write_feed`
  once on `league` rather than splitting into home/away.
- **Match location/duration:** edit `STADIUM` and the `timedelta(hours=2)`.

## Robustness

If the site layout changes and the scraper parses **zero** league matches, it
exits with an error instead of overwriting your good feeds with empty ones — so
a broken scrape fails visibly in the Actions tab rather than silently wiping
your calendars.
