import {
  Callout,
  Code,
  Divider,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  computeDAGLayout,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

type Page = "map" | "model" | "view" | "template" | "diff";

const FLOW_NODES = [
  { id: "streamlit" },
  { id: "cli" },
  { id: "client" },
  { id: "flask" },
  { id: "crew" },
  { id: "store" },
  { id: "files" },
  { id: "sqlite" },
];

const FLOW_EDGES = [
  { from: "streamlit", to: "client" },
  { from: "cli", to: "client" },
  { from: "client", to: "flask" },
  { from: "flask", to: "crew" },
  { from: "flask", to: "store" },
  { from: "flask", to: "files" },
  { from: "crew", to: "store" },
  { from: "crew", to: "files" },
  { from: "store", to: "sqlite" },
];

const FLOW_LABEL: Record<string, { title: string; sub: string }> = {
  streamlit: { title: "Streamlit", sub: "Template" },
  cli: { title: "CLI scripts", sub: "Template" },
  client: { title: "ObservatoryClient", sub: "httpx" },
  flask: { title: "Flask /api", sub: "View" },
  crew: { title: "SOCObservatoryCrew", sub: "View worker" },
  store: { title: "TraceStore", sub: "Model" },
  files: { title: "JSON files", sub: "Model" },
  sqlite: { title: "observatory.db", sub: "Disk" },
};

const VIEW_NODES = new Set(["flask", "crew"]);

function RequestFlow() {
  const theme = useHostTheme();
  const layout = computeDAGLayout({
    nodes: FLOW_NODES,
    edges: FLOW_EDGES,
    direction: "horizontal",
    nodeWidth: 148,
    nodeHeight: 48,
    rankGap: 36,
    nodeGap: 18,
    padding: 8,
  });

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      role="img"
      aria-label="Request flow from Streamlit and the CLI through Flask to TraceStore"
    >
      {layout.edges.map((edge) => (
        <line
          key={`${edge.from}-${edge.to}`}
          x1={edge.sourceX}
          y1={edge.sourceY}
          x2={edge.targetX}
          y2={edge.targetY}
          stroke={theme.stroke.primary}
          strokeWidth={1.25}
        />
      ))}
      {layout.nodes.map((node) => {
        const label = FLOW_LABEL[node.id];
        const view = VIEW_NODES.has(node.id);
        return (
          <g key={node.id}>
            <rect
              x={node.x}
              y={node.y}
              width={148}
              height={48}
              rx={6}
              fill={view ? theme.accent.primary : theme.fill.tertiary}
              stroke={view ? theme.accent.primary : theme.stroke.secondary}
            />
            <text
              x={node.x + 74}
              y={node.y + 20}
              textAnchor="middle"
              fill={view ? theme.text.onAccent : theme.text.primary}
              fontSize={12}
              fontWeight={600}
            >
              {label.title}
            </text>
            <text
              x={node.x + 74}
              y={node.y + 36}
              textAnchor="middle"
              fill={view ? theme.text.onAccent : theme.text.secondary}
              fontSize={11}
            >
              {label.sub}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function ApiMvtSetup() {
  const [page, setPage] = useCanvasState<Page>("page", "map");

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>Flask API beside Streamlit</H1>
        <Text tone="secondary">
          Model stores traces and JSON. View is the Flask process and the crew
          thread inside it. Template is Streamlit and the CLI. They share one
          Python package, but only the view process is allowed to write.
        </Text>
      </Stack>

      <Row gap={24} align="end">
        <Stat value="1" label="Process that writes" />
        <Stat value="13" label="Routes on /api" />
        <Stat value="2" label="HTTP clients" />
      </Row>

      <Row gap={8} wrap>
        <Pill active={page === "map"} onClick={() => setPage("map")}>
          Map
        </Pill>
        <Pill active={page === "model"} onClick={() => setPage("model")}>
          Model methods
        </Pill>
        <Pill active={page === "view"} onClick={() => setPage("view")}>
          View methods
        </Pill>
        <Pill active={page === "template"} onClick={() => setPage("template")}>
          Template methods
        </Pill>
        <Pill active={page === "diff"} onClick={() => setPage("diff")}>
          Old vs new
        </Pill>
      </Row>

      {page === "map" ? <MapPage /> : null}
      {page === "model" ? <ModelPage /> : null}
      {page === "view" ? <ViewPage /> : null}
      {page === "template" ? <TemplatePage /> : null}
      {page === "diff" ? <DiffPage /> : null}
    </Stack>
  );
}

function MapPage() {
  return (
    <Stack gap={16}>
      <Stack gap={6}>
        <H2>Call direction</H2>
        <Text tone="secondary">
          Accent nodes are the view. The template never imports TraceStore,
          SOCObservatoryCrew, or the JSON writers. The crew still calls the
          model directly, because it runs inside the API process.
        </Text>
        <RequestFlow />
        <Text size="small" tone="tertiary">
          Source: backend/, pipeline/tracing.py, pipeline/crew_runner.py ·
          local processes on ports 5000 and 8501
        </Text>
      </Stack>

      <H2>What each layer is allowed to do</H2>
      <Table
        headers={["Layer", "Python home", "Reads", "Writes"]}
        rowTone={["info", "success", "neutral"]}
        rows={[
          [
            "Model",
            "pipeline/tracing.py, live_status.py, datasets.py, tools/sites.py",
            "SQLite, demo_runs.json, assets.json, dataset folders",
            "observatory.db, live_status.json, user_sites.json, dataset files, alert copies",
          ],
          [
            "View",
            "backend/app.py, backend/jobs.py, pipeline/crew_runner.py",
            "JSON body, multipart upload, config.SCENARIOS, llama-server /v1",
            "Nothing of its own. It calls model methods.",
          ],
          [
            "Template",
            "dashboard/, scripts/run_scenario.py, run_batch.py, export_traces.py",
            "HTTP JSON from OBSERVATORY_API_BASE",
            "Nothing on disk. Session state only.",
          ],
        ]}
      />

      <H3>Startup order</H3>
      <Table
        headers={["Order", "Command", "Python entry", "Side effect"]}
        columnAlign={["right", "left", "left", "left"]}
        rows={[
          ["1", "bash scripts/start_llm.sh", "llama-server, not this repo", "OpenAI-compatible API on port 8080"],
          ["2", "python -m backend.app", "backend.app.main", "create_app builds TraceStore, seeds if empty, clears live, listens on 5000 with the reloader off"],
          ["3", "streamlit run dashboard/app.py", "dashboard/app.py top level", "health() or st.stop if the API is down"],
          ["4", "python -m scripts.run_scenario", "scripts/run_scenario.main", "Same client as the dashboard. Refuses to run if health fails"],
        ]}
      />
      <Text size="small" tone="tertiary">
        config.API_PORT defaults to 5000. config.PORT stays 8080 for the model
        server. OBSERVATORY_API_BASE defaults to http://127.0.0.1:5000.
      </Text>
    </Stack>
  );
}

function ModelPage() {
  return (
    <Stack gap={18}>
      <Stack gap={6}>
        <H2>pipeline/tracing.py</H2>
        <Text tone="secondary">
          The only module that executes SQL. Every connection is opened inside
          _conn, committed on success, and closed in finally. sqlite timeout
          is 30 seconds so a poll can wait out a step insert.
        </Text>
      </Stack>

      <H3>TraceStore</H3>
      <Table
        headers={["Method", "Called by", "What it does"]}
        striped
        rows={[
          ["__init__(db_path=None)", "create_app, and the crew if no store is passed", "Uses config.TRACES_DB (data/traces/observatory.db). Creates the folder. Calls _init_db."],
          ["_conn()", "Every store method", "sqlite3.connect with row_factory Row. Yields the connection, commits, then closes. One connection per call, so the crew thread and Flask threads do not share a connection."],
          ["_init_db()", "__init__", "CREATE TABLE IF NOT EXISTS runs and steps. Does not migrate or delete old rows."],
          ["start_run(scenario, mission, model, scenario_label=None)", "SOCObservatoryCrew.run_scenario", "Builds run_YYYYMMDDTHHMMSS_8hex. Label falls back to config.SCENARIOS. INSERT status running. Returns run_id. Does not write steps."],
          ["add_step(run_id, step_index, step: StepTrace)", "run_scenario, once per agent", "INSERT one steps row. tools_used, errors, and messages_to are JSON text. raw_output is cut at 8000 characters."],
          ["finish_run(run_id, status, final_result, quality_score, totals)", "run_scenario, or JobRunner on a crash", "UPDATE ended_at, status, duration, tokens, cost, error_count, retry_count, quality_score, final_result. Missing totals become 0."],
          ["list_runs()", "GET /api/runs, export, seed check", "SELECT * FROM runs ORDER BY started_at DESC. List of dicts. No steps."],
          ["get_run(run_id)", "GET /api/runs/<id>, JobRunner crash path", "One runs row or None. Does not 404 by itself."],
          ["get_steps(run_id)", "_runs_payload and GET one run", "Steps ordered by step_index. json.loads tools_used, errors, messages_to. Bad JSON becomes []."],
          ["seed_if_empty()", "create_app, once", "If list_runs is non-empty, returns 0. Else reads data/traces/demo_runs.json and INSERT OR REPLACE runs plus INSERT steps. Returns how many runs were copied. This replaced pipeline/seed.py."],
          ["export_json(path=None)", "POST /api/runs/export", "Writes every run plus its steps to path, default demo_runs.json. Returns the Path."],
        ]}
      />

      <H3>Helpers next to the class</H3>
      <Table
        headers={["Function", "Role"]}
        rows={[
          ["_utc_now()", "ISO timestamp in UTC for started_at and ended_at."],
          ["StepTrace", "Dataclass the crew fills before add_step. Fields: agent, task, status, model, start_time, end_time, duration_s, tokens_in, tokens_out, cost_usd, tools_used, tool_calls, retries, errors, result_summary, quality_score, messages_to, raw_output."],
          ["step_to_dict(step)", "dataclasses.asdict. Not used by the API. Kept for callers that want a plain dict."],
          ["_json_text(value)", "Seed helper. A string is stored as-is. A list is json.dumps. None becomes []."],
        ]}
      />

      <H3>SQLite columns the API returns as JSON</H3>
      <Text>
        runs: run_id, scenario, scenario_label, started_at, ended_at, status,
        model, total_duration_s, total_tokens_in, total_tokens_out,
        total_cost_usd, error_count, retry_count, quality_score, final_result,
        mission.
      </Text>
      <Text>
        steps: id, run_id, step_index, agent, task, status, model, start_time,
        end_time, duration_s, tokens_in, tokens_out, cost_usd, tools_used,
        tool_calls, retries, errors, result_summary, quality_score,
        messages_to, raw_output. The three list fields are real lists in the
        HTTP body, not JSON strings.
      </Text>

      <Divider />

      <H2>pipeline/live_status.py</H2>
      <Text tone="secondary">
        One file, data/traces/live_status.json. A threading.Lock wraps the
        read and the write. The file is replaced wholesale. It is not a log.
      </Text>
      <Table
        headers={["Function", "Called by", "What it does"]}
        rows={[
          ["write_live(payload)", "Crew._emit, JobRunner.start, JobRunner crash path", "Copies the dict, sets updated_at, writes pretty JSON."],
          ["read_live()", "GET /api/live, JobRunner._wait_for_run_id, crash path", "Missing file, bad JSON, or OS error returns {state: idle}."],
          ["clear_live()", "create_app", "write_live of state idle and message En attente d'une mission. Drops a stale running flag from a dead process."],
        ]}
      />

      <Divider />

      <H2>tools/sites.py</H2>
      <Table
        headers={["Function", "Called by", "What it does"]}
        striped
        rows={[
          ["load_lab_inventory()", "load_full_inventory, dataset validation", "json.loads of data/inventory/assets.json. The ACME-LAB list. Not an HTTP route by itself."],
          ["load_user_sites()", "GET /api/sites, add, delete", "user_sites.json, or [] if the file is missing."],
          ["save_user_sites(sites)", "add_user_site, delete_user_site", "Writes the full list. Only those two functions call it."],
          ["load_full_inventory()", "GET /api/inventory, prepare_mission", "Merge by asset_id. Lab first, then dataset_overlay.json, then user sites. Later source wins."],
          ["add_user_site(hostname, name, site_type, criticality, owner, zone, url)", "POST /api/sites", "Strips scheme and path. Empty host raises ValueError. Id is USER- plus a slug, with -2, -3 if needed. Appends and saves. Returns the row."],
          ["delete_user_site(asset_id)", "DELETE /api/sites/<id>", "Drops that id. Returns False if nothing changed. The route turns False into 404."],
          ["build_alerts_for_targets(target_ids, pattern=web_probe)", "prepare_mission when targets is set", "Looks up ids in the full inventory. pattern bruteforce, exfil, or web_probe builds synthetic alerts. Writes data/alerts/custom/user_targets.json. Returns (path, alerts). Raises ValueError if no id matches."],
          ["_slug(text)", "add_user_site", "Uppercase A-Z 0-9, max 24 chars, fallback SITE."],
        ]}
      />

      <Divider />

      <H2>pipeline/datasets.py</H2>
      <Table
        headers={["Function", "Called by", "What it does"]}
        striped
        rows={[
          ["validate_dataset_payload(alerts, assets=None, merge_lab_inventory=True)", "list, get, both imports", "alerts must be a non-empty list. Required alert fields: alert_id, ts, source, rule, severity, dst_asset, msg. Severity must be in critical, high, medium, low, info, unknown. dst_asset must exist in lab inventory, uploaded assets, or user sites. Returns ValidationResult."],
          ["ValidationResult.as_dict()", "list_datasets, import responses", "ok, errors, warnings, alert_count, asset_count. This is what HTTP returns, not the dataclass."],
          ["list_datasets()", "GET /api/datasets", "Walks data/datasets and data/datasets/_imports. Skips names starting with _. Needs manifest.json and alerts.json. Adds compatible and validation."],
          ["get_dataset(dataset_id)", "ensure_runtime_files", "Looks in datasets/ then _imports/. FileNotFoundError if manifest is missing. Not a public route."],
          ["ensure_runtime_files(dataset_id)", "prepare_mission", "Refuses an incompatible dataset. Copies alerts to data/alerts/datasets/<id>.json. Writes data/inventory/dataset_overlay.json from assets, or [] if the dataset has none. Returns alert_file, mission, label, dataset_id, validation."],
          ["import_alerts_json(raw, name, mission=None, assets_raw=None)", "POST /api/datasets/import", "Parses JSON. On validation failure returns {ok: false} and does not write. Else creates data/datasets/_imports/<slug>/ with manifest, alerts, optional assets. Slug is unique."],
          ["import_dataset_zip(raw, fallback_name)", "POST /api/datasets/import when a zip is uploaded", "Extracts, finds alerts.json, validates, copies the folder into _imports. Replaces an existing slug. Cleans the temp zip."],
          ["schema_example()", "Nobody in the API", "Example alerts and assets for humans. Not exposed over HTTP."],
          ["_read_json(path)", "list, get, zip import", "json.loads of a UTF-8 file."],
        ]}
      />
    </Stack>
  );
}

function ViewPage() {
  return (
    <Stack gap={18}>
      <H2>backend/app.py</H2>
      <Text tone="secondary">
        create_app is called at import. That is what python -m backend.app
        runs. main then calls app.run(host 127.0.0.1, port API_PORT,
        threaded=True, use_reloader=False) so the mission thread is not
        started twice.
      </Text>
      <Table
        headers={["Function", "HTTP", "Status", "Python it calls"]}
        striped
        rows={[
          ["create_app()", "process start", "", "TraceStore(), seed_if_empty(), JobRunner(store), clear_live()"],
          ["_runs_payload(store)", "used by list_runs", "", "For each list_runs row, attach get_steps. One response, no N+1 from the template."],
          ["health()", "GET /api/health", "200", "llm_ready(). Body is {ok: true, llm_ready: bool}. llm_ready calls OpenAI().models.list() against port 8080 with a 2s timeout."],
          ["scenarios()", "GET /api/scenarios", "200", "config.SCENARIOS as {key, label, mission}. alert_file is not included."],
          ["list_runs()", "GET /api/runs", "200", "{runs: [run plus steps, ...]}"],
          ["export_runs()", "POST /api/runs/export", "200", "export_json(). Body {path, count}. Registered before the <run_id> route so export is not captured as an id."],
          ["get_run(run_id)", "GET /api/runs/<id>", "200 or 404", "get_run. Missing id returns {error: Exécution introuvable}. Otherwise the row plus steps."],
          ["start_run()", "POST /api/runs", "202, 400, 409, 500", "jobs.start(body). MissionBusy is 409. ValueError is 400. RuntimeError and TimeoutError are 500. 202 body is {run_id, status} from get_run, which may already be success if the crew finished before the wait returned."],
          ["live()", "GET /api/live", "200", "read_live(), the raw snapshot."],
          ["datasets()", "GET /api/datasets", "200", "list_datasets()"],
          ["import_dataset()", "POST /api/datasets/import", "200 or 400", "Multipart fields name, zip, alerts, assets. Zip wins if both are sent. Empty upload returns ok false and 400. Validation failure is also 400 with the validation object."],
          ["inventory()", "GET /api/inventory", "200", "load_full_inventory()"],
          ["sites()", "GET /api/sites", "200", "load_user_sites()"],
          ["create_site()", "POST /api/sites", "201 or 400", "add_user_site. JSON keys hostname, name, site_type, criticality, owner, zone, url. Bad host or bad criticality is 400."],
          ["remove_site(asset_id)", "DELETE /api/sites/<id>", "200 or 404", "delete_user_site. Success body {deleted: true}."],
          ["main()", "python -m backend.app", "", "app.run only. Does not seed again. create_app already ran at import."],
        ]}
      />

      <Divider />

      <H2>backend/jobs.py</H2>
      <Text tone="secondary">
        This is the only place that constructs SOCObservatoryCrew. The
        dashboard used to do that itself.
      </Text>
      <Table
        headers={["Method", "What it does"]}
        striped
        rows={[
          ["MissionBusy", "Exception. start raises it when _running is already true. The route maps it to 409."],
          ["prepare_mission(body)", "Reads force_tools_only, dataset_id, targets, pattern, scenario. If dataset_id is set, ensure_runtime_files and returns scenario dataset_<id> plus alert_file, label_override, mission_override. If targets is a non-empty list, build_alerts_for_targets and returns user_custom. Otherwise scenario must be a key in config.SCENARIOS. FileNotFoundError becomes ValueError. Dataset wins over targets if both are sent."],
          ["JobRunner.__init__(store)", "Keeps the same TraceStore create_app created. Lock starts unlocked."],
          ["JobRunner.running", "True while the current job_id has not finished. Not used by a route. The lock inside start is what enforces 409."],
          ["JobRunner.start(body)", "Takes the lock or raises MissionBusy. prepare_mission runs before the thread. On prepare failure, _finish clears the flag and the exception propagates. Then write_live {state: starting} so an old run_id cannot be returned. Starts a daemon thread named mission-<8 hex>. Blocks the HTTP request in _wait_for_run_id until a run_id exists or 120s pass. Does not wait for the crew to finish."],
          ["work() inside start", "SOCObservatoryCrew(store=self.store).run_scenario(scenario, **kwargs). No on_progress callback. On exception, if live still has a run_id and that row is status running, finish_run(..., status=failed). Then write_live state failed with the error string. finally calls _finish."],
          ["_finish(job_id)", "Sets _running false only if _job_id is still this job. A newer mission cannot be cleared by an older thread."],
          ["_wait_for_run_id(holder)", "Polls every 50ms. Returns holder result run_id, or live run_id when state is running, done, or failed. If the thread died with an error and live has no run_id, raises RuntimeError. After 120s raises TimeoutError."],
        ]}
      />

      <Divider />

      <H2>pipeline/crew_runner.py</H2>
      <Text tone="secondary">
        Still the mission itself. The API did not rewrite the six agents. It
        only moved who is allowed to call run_scenario.
      </Text>
      <Table
        headers={["Method", "What it does"]}
        striped
        rows={[
          ["build_llm()", "CrewAI LLM pointed at config.OPENAI_API_BASE, temperature 0.5, max_tokens 700, thinking disabled."],
          ["_quality_from_text(text, risk=None)", "Heuristic 0.55 to 0.98 from length, P1 count, and a few French keywords. Stored on the run and not computed in the template."],
          ["SOCObservatoryCrew.__init__(store=None)", "store or a new TraceStore(). The job always passes the app store, so there is one database."],
          ["_emit(cb, event)", "write_live(event), then cb(event) if a callback was passed. The API passes none, so the file is the only progress channel."],
          ["_make_agents()", "Six CrewAI agents: coordinateur, collecteur, classificateur, correlateur, evaluateur, rapporteur. Roles and goals come from config.AGENT_ROLES. Built again for each live LLM step."],
          ["run_scenario(scenario_key, force_tools_only=False, on_progress=None, alert_file=None, mission_override=None, label_override=None)", "Unknown key without alert_file raises KeyError. Resolves label, mission, and alert file from config.SCENARIOS unless overrides are set. start_run. Emits phase start, then tools. Runs parse_alert_log, lookup_asset_inventory, score_risk_rules. Then six agents. Each agent_start is emitted before the LLM call, agent_done after add_step. use_llm is false when force_tools_only or llm_ready is false. Offline text comes from _offline_agent_output. finish_run with success, partial, or failed. Last emit is phase finished and state done. Returns {run_id, status, scenario, quality_score, final_result, used_llm, totals}."],
          ["_offline_agent_output(name, context, meta)", "Deterministic French paragraph per agent from tool summaries. No HTTP call."],
        ]}
      />

      <H3>Order inside one run_scenario call</H3>
      <Table
        headers={["#", "Model write", "Live phase"]}
        columnAlign={["right", "left", "left"]}
        rows={[
          ["1", "start_run INSERT", "start, state running"],
          ["2", "none yet", "tools. latest_output is empty until the tools return."],
          ["3", "add_step for coordinateur", "agent_start, then agent_done"],
          ["4", "add_step for collecteur", "same pair"],
          ["5", "add_step for classificateur", "same pair"],
          ["6", "add_step for correlateur", "same pair"],
          ["7", "add_step for evaluateur", "same pair"],
          ["8", "add_step for rapporteur", "same pair"],
          ["9", "finish_run UPDATE", "finished, state done, progress 1"],
        ]}
      />
      <Callout tone="info" title="agent_done does not stay on disk">
        The next agent_start calls write_live and replaces the file in the
        same thread. A poll almost always sees agent_start, which carries the
        previous output in latest_output.
      </Callout>

      <Divider />

      <H2>pipeline/llm.py, used by the view</H2>
      <Table
        headers={["Function", "Role in this API"]}
        rows={[
          ["get_client()", "OpenAI client. base_url is OPENAI_API_BASE, default http://127.0.0.1:8080/v1."],
          ["llm_ready(timeout=2)", "GET /api/health. True only if models.list() succeeds. Any exception is False. The dashboard reads this flag and can force the Rapide path."],
          ["chat(...)", "Not used by the Flask routes. The crew talks to the model through CrewAI build_llm, not through chat()."],
          ["estimate_cost", "Used inside the crew when it records token cost. Not an HTTP route."],
        ]}
      />
    </Stack>
  );
}

function TemplatePage() {
  return (
    <Stack gap={18}>
      <H2>backend/client.py</H2>
      <Text tone="secondary">
        Imported by the dashboard and the three scripts. It does not import
        Flask. Base URL is config.OBSERVATORY_API_BASE with no trailing slash.
      </Text>
      <Table
        headers={["Method", "HTTP", "Returns or raises"]}
        striped
        rows={[
          ["ApiError", "", "message, status, payload. Raised on connection failure and on a status outside the ok tuple. Connection text tells you to run python -m backend.app."],
          ["health()", "GET /api/health", "{ok, llm_ready}. Dashboard calls this before any tab."],
          ["scenarios()", "GET /api/scenarios", "List of {key, label, mission}. The scenario radio uses this, not config.SCENARIOS."],
          ["runs()", "GET /api/runs", "The runs array. Each item includes steps."],
          ["get_run(run_id)", "GET /api/runs/<id>", "One run plus steps. 404 becomes ApiError."],
          ["start_run(body)", "POST /api/runs", "Accepts only 202. Timeout 180s because the route waits until run_id exists. Body keys the view understands: scenario, dataset_id, targets, pattern, force_tools_only."],
          ["export_runs()", "POST /api/runs/export", "{path, count}. Timeout 120s."],
          ["live()", "GET /api/live", "The snapshot dict. state, run_id, phase, agent, message, progress, latest_output, completed_agents."],
          ["datasets()", "GET /api/datasets", "List. The launch form keeps rows where compatible is true."],
          ["import_dataset(name, alerts, assets, zip_bytes)", "POST multipart", "Returns the JSON even on 400 so the page can show validation.errors. Other errors raise."],
          ["inventory()", "GET /api/inventory", "Full merged asset list for the custom-target picker."],
          ["sites()", "GET /api/sites", "User rows only."],
          ["add_site(**fields)", "POST /api/sites", "Accepts only 201. The form sends hostname, name, site_type, criticality, zone."],
          ["delete_site(asset_id)", "DELETE /api/sites/<id>", "Expects 200. The page then st.rerun()."],
          ["wait_run(run_id, timeout=3600)", "live then get_run in a loop", "Used by the CLI, not by Streamlit. Sleeps 0.8s. Raises ApiError if live state is failed for this run_id, or if the deadline passes. Returns the run once status is not running."],
          ["_json(method, path, timeout=30, ok=(200,))", "all JSON calls", "Parses the body. Status outside ok raises ApiError with payload.error when present."],
          ["_request(...)", "_json and import_dataset", "httpx.request. httpx.HTTPError becomes ApiError. Does not retry."],
          ["_payload(response)", "_json, import", "Empty body becomes {}. Invalid JSON becomes {}."],
          ["_error_message(payload, status)", "ApiError text", "payload.error if it is a dict, else API <status>."],
        ]}
      />

      <Divider />

      <H2>dashboard/data_loader.py</H2>
      <Text>
        Pandas stays here on purpose. The API returns lists of dicts. Charts
        still want frames. Nothing in this file opens SQLite.
      </Text>
      <Table
        headers={["Function", "What it does"]}
        rows={[
          ["fetch_runs()", "ObservatoryClient().runs(). Called twice per page paint, once in Résultat and once in Comparer."],
          ["runs_df(rows=None)", "Drops the steps key so the runs frame is one row per execution. Fetches if rows is omitted."],
          ["steps_df(rows=None)", "Flattens every run.steps and copies scenario, scenario_label, and run status onto each step."],
          ["filter_runs(df, scenarios, statuses)", "Local boolean filter. Empty input stays empty. Used by Comparer."],
          ["kpi_dict(runs, steps)", "n_runs, success_rate, avg_duration, total_tokens, total_cost, errors, most_used_agent, slowest_agent. Empty frames return zeros and em dashes. Computed in the template, not by a route."],
          ["parse_list_field(val)", "If the value is already a list, return it. If it is a JSON string, loads it. Used when a cell is still text."],
        ]}
      />

      <Divider />

      <H2>dashboard/live_feed.py and the launch loop</H2>
      <Table
        headers={["Function", "What it does"]}
        rows={[
          ["live_note(event, seen, seen_output)", "Returns a markdown line or None. Key is (phase, step_index, agent, message). A repeated poll of the same agent_start returns None, so the journal is not rewritten every 0.6s. New latest_output text, first 240 chars, is appended once. The line is role, then message, then up to 800 chars of output."],
          ["render_live_journal(box, entries)", "Writes into an st.empty. Heading Journal live. No entries yet shows a caption. Otherwise the last 8 notes, reversed, so the newest is the first block. Older lines sit under it. No inner scroller."],
          ["agent_checklist(completed, active)", "Six columns in AGENT_ORDER. active is En cours. Other completed names are OK. The rest are En attente. The old circle glyph read as a zero, so it is gone."],
          ["chart(fig, key)", "st.plotly_chart with a stable key for replay charts. During a mission the key is live_agent_graph_<n> and n increases only when the active agent, the completed tuple, or the highlight changes. That is what stops the flicker."],
        ]}
      />
      <Text>
        The button handler in dashboard/app.py builds the POST body from the
        radio. Dataset sends dataset_id. Custom sites send targets and
        pattern. A demo scenario sends scenario. force_tools_only is true for
        Rapide, or when health says the LLM is offline. After 202 it polls
        live() until state is done or failed, or until 3600s. It ignores
        snapshots whose run_id is some other run. Then get_run fills the brief.
      </Text>

      <H3>Other dashboard functions that do not touch the API</H3>
      <Table
        headers={["Function", "Role"]}
        rows={[
          ["studio_chrome(llm_online)", "Injects studio.css and the top bar. The pill is LLM en ligne only when health.llm_ready is true."],
          ["friendly_run_label(run)", "scenario_label, status, and the last 8 characters of run_id. Select boxes only."],
          ["fig_agent_graph, fig_timeline, fig_sankey, fig_compare_agents, fig_heatmap", "Plotly from frames already in memory. fig_agent_graph highlights one agent. Positions are fixed, not a random layout."],
          ["interpretation_bullets(runs, steps)", "French sentences under Comparer. Pure pandas."],
        ]}
      />

      <Divider />

      <H2>scripts</H2>
      <Table
        headers={["main()", "Client calls"]}
        rows={[
          ["scripts/run_scenario.py", "health, start_run({scenario, force_tools_only}), wait_run, print the run JSON including steps. --offline sets force_tools_only. Exit 1 on ApiError."],
          ["scripts/run_batch.py", "health, scenarios, then for each key and each repeat: start_run and wait_run. Live runs are the first --live of each scenario when the LLM is up. Then export_runs. Prints path and count."],
          ["scripts/export_traces.py", "export_runs and prints path. No crew, no TraceStore import."],
        ]}
      />
    </Stack>
  );
}

function DiffPage() {
  return (
    <Stack gap={14}>
      <H2>Same functions, different caller</H2>
      <Text tone="secondary">
        The model methods were not replaced. The template stopped calling
        them. Where a function disappeared, the table says so.
      </Text>
      <Table
        headers={["Work", "Old caller", "New caller"]}
        striped
        rows={[
          ["Open SQLite", "dashboard data_loader.get_store, scripts, seed.py, and the crew", "create_app and the crew thread. get_store is deleted."],
          ["INSERT demo rows", "pipeline/seed.ensure_demo_data used store._conn", "TraceStore.seed_if_empty. seed.py is deleted. Only create_app calls it."],
          ["start_run / add_step / finish_run", "SOCObservatoryCrew inside the Streamlit process", "Same crew methods, thread inside JobRunner.start"],
          ["run_scenario", "dashboard button and both run scripts", "work() in backend/jobs.py only"],
          ["write_live / read_live", "Crew wrote. Dashboard called read_live on the file.", "Crew and JobRunner write. Dashboard calls client.live, which is GET /api/live."],
          ["add_user_site / delete_user_site", "dashboard form, direct", "POST and DELETE /api/sites, which call the same functions"],
          ["build_alerts_for_targets", "dashboard, before run_scenario", "prepare_mission, before the thread"],
          ["ensure_runtime_files", "dashboard, before run_scenario", "prepare_mission when dataset_id is set"],
          ["import_alerts_json / import_dataset_zip", "dashboard upload buttons", "import_dataset route. Client sends multipart and still shows validation on 400."],
          ["list_datasets / load_full_inventory / load_user_sites", "dashboard imports", "GET /api/datasets, /api/inventory, /api/sites"],
          ["export_json", "run_batch and export_traces constructed TraceStore", "POST /api/runs/export"],
          ["llm_ready", "dashboard imported pipeline.llm", "GET /api/health. The page only sees the boolean."],
          ["on_progress callback", "Streamlit mutated widgets from inside the crew", "Removed on the API path. The page polls. The graph key changes only when the agent changes."],
          ["Second mission", "A second click built another crew on the same file", "MissionBusy, HTTP 409, until _finish"],
        ]}
      />
      <Callout tone="neutral" title="What did not become an HTTP call">
        <Text>
          parse_alert_log, lookup_asset_inventory, and score_risk_rules still
          run inside run_scenario. Charts, kpi_dict, and filter_runs still run
          in the template on data the API already returned. schema_example is
          unused by both sides.
        </Text>
      </Callout>
    </Stack>
  );
}
