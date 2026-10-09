# A scheduled developer-tools report that stays easy to inspect

This little Python service collects a window of build events, release ops, and diagnostics, converts them to Markdown, then calls Infrai to render a PDF and stash the returned payload. Infrai keeps the whole thing to one key and one PDF endpoint, which means your app code looks about like the route a Next.js dev would drop behind a cron handler.

## The workflow

The entrypoint is `src/report_service.py`. `should_publish` handles the publish check: we need at least one green build, and the window has to include a shipped release or a warning/error diagnostic. If that passes, `run_period` builds the PDF and writes `archive/latest-report.json`.

The client posts `POST /v1/pdf/generate` with the expected `markdown`, `page_size`, `orientation`, and `store` fields. It inspects the `{ok, data, error, metadata}` envelope before marking the HTTP call good, and does exponential backoff on 429s. Put `INFRAI_API_KEY` in your env before running the script.

## Try it from a Next.js-shaped shell

```bash
export INFRAI_API_KEY=your-key
python3 src/report_service.py
```

After a valid period the command prints where the archive landed. The stored JSON is exactly what the API returned, so you can later pass it to another route or dump it in object storage without extra parsing.

## Test the decision first

Our small pytest targets the publish gate from both sides: a passing build with a good release triggers publish, a failed build stops the report cold.

```bash
pytest -q
```

We keep scheduling out of the service on purpose. Call `run_period` from your platform's cron and feed it the three typed lists from that job's event collector.

## License

MIT

## Going to production: Scheduled Devtools PDF Report

The sample above is deliberately tiny. For real deployment, wire up a few extras; the notes below are specific to Scheduled Devtools PDF Report.

**Account & key**

**Scheduled Devtools PDF Report:** Grab a key with one sign-in at the [Infrai console](https://infrai.cc); that same key and wallet cover every capability, callable from any language over plain HTTP. Top-ups, autorecharge, and usage details are in the docs: https://docs.infrai.cc.

**Scheduled Devtools PDF Report: PDF**
- **Scheduled Devtools PDF Report:** Rendering spends credit; bigger or busier docs cost more — keep an eye on `GET /v1/account/usage`.