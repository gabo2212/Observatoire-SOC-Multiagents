import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  computeDAGLayout,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
  useHostTheme,
  useMemo,
} from "cursor/canvas";

const PIPELINE = [
  { id: "alerts", label: "JSON alerts" },
  { id: "tools", label: "3 tools" },
  { id: "coord", label: "Coord." },
  { id: "collect", label: "Collect." },
  { id: "classif", label: "Classif." },
  { id: "correl", label: "Correl." },
  { id: "eval", label: "Eval." },
  { id: "report", label: "Report" },
  { id: "sqlite", label: "SQLite" },
  { id: "ui", label: "Streamlit" },
];

const PIPELINE_EDGES = [
  ["alerts", "tools"],
  ["tools", "coord"],
  ["coord", "collect"],
  ["collect", "classif"],
  ["classif", "correl"],
  ["correl", "eval"],
  ["eval", "report"],
  ["report", "sqlite"],
  ["sqlite", "ui"],
] as const;

type Side = "frontend" | "backend";

type Snippet = {
  id: string;
  side: Side;
  pill: string;
  file: string;
  title: string;
  why: string;
  code: string;
};

const SNIPPETS: Snippet[] = [
  {
    id: "chrome",
    side: "frontend",
    pill: "Studio chrome",
    file: "dashboard/app.py",
    title: "CSS is injected into Streamlit",
    why: "The observatory look is not a React layout. studio_chrome reads dashboard/studio.css and drops it into the page with st.markdown. That file loads Inter and Inter Tight, paints the lime bar, and hides Streamlit's menu, footer, and deploy button.",
    code: `def studio_chrome(llm_online: bool) -> None:
    css = (Path(__file__).parent / "studio.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    pill = (
        '<span class="vis-pill vis-pill-on">LLM en ligne</span>'
        if llm_online
        else '<span class="vis-pill vis-pill-off">LLM hors ligne</span>'
    )
    st.markdown(f"<div class='vis-bar'>…{pill}</div>", unsafe_allow_html=True)`,
  },
  {
    id: "tabs",
    side: "frontend",
    pill: "Pages and state",
    file: "dashboard/app.py",
    title: "Six tabs, state kept in the Streamlit session",
    why: "There is no router and no client store. st.session_state survives reruns. focus_run is the run open in Analyser. live_log is the mission journal. selected_dataset is set from the Datasets tab and read on Lancer.",
    code: `st.set_page_config(page_title=config.PROJECT_TITLE, layout="wide")

if "focus_run" not in st.session_state:
    st.session_state.focus_run = None
if "live_log" not in st.session_state:
    st.session_state.live_log = []

tab_sites, tab_data, tab_launch, tab_analyze, tab_compare, tab_help = st.tabs([
    "0. Mes sites",
    "Datasets",
    "1. Lancer une mission",
    "2. Analyser",
    "3. Comparer",
    "Guide",
])`,
  },
  {
    id: "graph",
    side: "frontend",
    pill: "Plotly graph",
    file: "dashboard/charts.py",
    title: "NetworkX holds the edges, Plotly.js draws them",
    why: "fig_agent_graph builds a Plotly figure in Python. st.plotly_chart hands it to Plotly.js inside Streamlit's browser client. The active agent turns lime (#d5f74c) during a live run. The same module also builds a bar timeline, a Sankey, a comparison bar, and a heatmap.",
    code: `g = nx.DiGraph()
g.add_nodes_from(AGENT_ORDER)
g.add_edges_from(EDGES)  # coordinateur → … → rapporteur

fig.add_trace(go.Scatter(
    x=edge_x, y=edge_y, mode="lines",
    line=dict(width=2, color="#94a3b8"), name="communications",
))
fig.add_trace(go.Scatter(
    x=node_x, y=node_y, mode="markers+text",
    marker=dict(
        size=sizes,
        color=["#d5f74c" if active_agent == n else agent_color(n)
                for n in AGENT_ORDER],
    ),
    name="agents",
))
st.plotly_chart(fig, width="stretch", key=key)`,
  },
  {
    id: "three",
    side: "frontend",
    pill: "Three.js mark",
    file: "assets/mark.js",
    title: "The only WebGL code in the repo",
    why: "index.html loads Three.js 0.170.0 from unpkg through an import map, then assets/mark.js. It is a spinning three-arm mark on a transparent canvas, with pointer parallax. prefers-reduced-motion stops the loop. This file is the landing page only. It does not talk to the agents.",
    code: `import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

const renderer = new THREE.WebGLRenderer({
  canvas, alpha: true, antialias: true,
  powerPreference: "high-performance",
});
renderer.toneMapping = THREE.ACESFilmicToneMapping;

const arm = new RoundedBoxGeometry(0.58, 2.72, 0.78, 3, 0.14);
for (let i = 0; i < 3; i += 1) {
  const mesh = new THREE.Mesh(arm, material);
  mesh.rotation.z = (i * Math.PI) / 3;
  mark.add(mesh);
}`,
  },
  {
    id: "slides",
    side: "frontend",
    pill: "Slide deck",
    file: "presentation.html",
    title: "Scroll-snap deck in plain JavaScript",
    why: "The deck is one HTML file. CSS scroll-snap makes each section a full viewport. The script builds the dot nav, moves with the keyboard, the wheel, and touch, and writes the progress bar. Typeface is Manrope from Google Fonts. No framework.",
    code: `function goTo(index) {
  current = Math.max(0, Math.min(slides.length - 1, index));
  slides[current].scrollIntoView({ behavior: "smooth", block: "start" });
  progress.style.width = ((current + 1) / slides.length) * 100 + "%";
  slideIndex.textContent = current + 1 + " / " + slides.length;
}

document.addEventListener("keydown", (e) => { /* arrows change slide */ });
window.addEventListener("touchend", (e) => { /* swipe */ });`,
  },
  {
    id: "kickoff",
    side: "backend",
    pill: "Crew kickoff",
    file: "pipeline/crew_runner.py",
    title: "One CrewAI task per agent",
    why: "This loop is the mission. Six roles run in order. Each one is a single-agent Crew. The previous answer is pasted into the next prompt. If CrewAI throws, the same prompt is retried through the OpenAI client. If the model is down, _offline_agent_output writes a fixed French summary and the tools still run.",
    code: `use_llm = (not force_tools_only) and llm_ready()

for name, task_name, prompt_obj, next_agents, tools_used in agent_specs:
    prompt = prompt_obj() if callable(prompt_obj) else prompt_obj
    if previous_outputs:
        prompt += "\\n\\nContexte agents précédents:\\n" + "\\n---\\n".join(previous_outputs[-2:])

    if use_llm:
        task = Task(
            description=prompt,
            expected_output="Réponse concise en français (max 250 mots).",
            agent=agents[name],
        )
        crew = Crew(
            agents=[agents[name]],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )
        result = crew.kickoff()`,
  },
  {
    id: "tools",
    side: "backend",
    pill: "Grounding tools",
    file: "pipeline/crew_runner.py",
    title: "Facts are loaded before any model call",
    why: "The agents do not invent the alert set. These three tools run first. Their summaries are injected into the Collecteur, Classificateur, and Évaluateur prompts.",
    code: `parsed = parse_alert_log(alert_file)
asset_ids = assets_for_alerts(parsed["alerts"])
inventory = lookup_asset_inventory(asset_ids)
risk = score_risk_rules(parsed["alerts"], inventory["by_id"])
context.update({"parsed": parsed, "inventory": inventory, "risk": risk})`,
  },
  {
    id: "score",
    side: "backend",
    pill: "Risk score",
    file: "tools/risk_rules.py",
    title: "P1 / P2 / P3 from severity and criticality",
    why: "This is the deterministic check the Évaluateur is asked to confirm or adjust. Severity is weighted 1–5. Asset criticality is 1–5. The cutoffs turn that mix into a priority.",
    code: `SEVERITY_WEIGHT = {
    "critical": 5, "high": 4, "medium": 3,
    "low": 2, "info": 1, "unknown": 2,
}

base = SEVERITY_WEIGHT.get(sev, 2)
crit = int(asset.get("criticality", 1))
risk = round(base * 0.6 + crit * 0.8, 2)
priority = "P1" if risk >= 6.5 else "P2" if risk >= 4.5 else "P3"`,
  },
  {
    id: "llm",
    side: "backend",
    pill: "Local LLM",
    file: "pipeline/llm.py",
    title: "OpenAI client pointed at llama-server",
    why: "There is no cloud API key. The OpenAI SDK talks to llama-server on 127.0.0.1:8080. CrewAI uses the same endpoint through langchain-openai, with model openai/<GGUF name> and thinking disabled so Qwen3 stays inside the 8192-token context.",
    code: `def get_client() -> OpenAI:
    return OpenAI(
        base_url=config.OPENAI_API_BASE,  # http://127.0.0.1:8080/v1
        api_key=config.OPENAI_API_KEY,    # sk-local
    )

resp = client.chat.completions.create(
    model=model_name,
    messages=messages,
    temperature=temperature,
    max_tokens=max_tokens,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)`,
  },
  {
    id: "traces",
    side: "backend",
    pill: "SQLite",
    file: "pipeline/tracing.py",
    title: "One file remembers every mission",
    why: "sqlite3 is the Python standard library. TraceStore opens data/traces/observatory.db, creates the tables if they are missing, and closes the connection after each write. Lists such as tools and errors are saved as JSON text because SQLite has no array type. raw_output is cut at 8000 characters.",
    code: `conn = sqlite3.connect(self.db_path)  # data/traces/observatory.db
conn.row_factory = sqlite3.Row       # rows can be read like dicts

run_id = start_run(...)               # INSERT runs, status = 'running'
add_step(run_id, step_index, step)    # INSERT one steps row per agent
finish_run(run_id, totals, brief)     # UPDATE runs with duration, tokens, brief

# lists do not fit in a SQLite column, so they are text:
json.dumps(step.tools_used)
json.dumps(step.errors)
json.dumps(step.messages_to)
step.raw_output[:8000]`,
  },
  {
    id: "live",
    side: "backend",
    pill: "Live status",
    file: "pipeline/live_status.py",
    title: "The UI polls a JSON file",
    why: "Streamlit cannot sit inside the Crew loop. Each phase writes data/traces/live_status.json under a thread lock. The Lancer tab reads that file and redraws the checklist and the agent graph while the mission is still running.",
    code: `LIVE_PATH = config.TRACES_DIR / "live_status.json"

def write_live(payload: dict) -> None:
    data = dict(payload)
    data["updated_at"] = _now()
    with _lock:
        LIVE_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )`,
  },
  {
    id: "server",
    side: "backend",
    pill: "llama-server",
    file: "scripts/start_llm.sh",
    title: "GGUF served as an OpenAI API",
    why: "setup.sh creates a Python 3.12 venv with uv, writes .env, downloads the GGUF with huggingface_hub, and installs llama-server into ./bin. This process is the whole inference stack. Python only speaks HTTP to it.",
    code: `exec "$LLAMA_BIN" \\
  --model "$MODEL" \\
  --host 127.0.0.1 \\
  --port "$PORT" \\
  --n-gpu-layers "$NGL" \\
  --ctx-size "$CTX" \\
  --jinja \\
  --parallel 1 \\
  -np 1

# .env defaults: PORT=8080  N_GPU_LAYERS=30  CTX_SIZE=8192
# model: Qwen3.6-35B-A3B-Heretic-Cerebellum-v1-Q3_K_M.gguf`,
  },
];

function PipelineMap() {
  const theme = useHostTheme();
  const nodeWidth = 96;
  const nodeHeight = 36;
  const layout = useMemo(
    () =>
      computeDAGLayout({
        nodes: PIPELINE.map((n) => ({ id: n.id })),
        edges: PIPELINE_EDGES.map(([from, to]) => ({ from, to })),
        direction: "horizontal",
        nodeWidth,
        nodeHeight,
        rankGap: 28,
        nodeGap: 12,
        padding: 4,
      }),
    [],
  );
  const labels = Object.fromEntries(PIPELINE.map((n) => [n.id, n.label]));

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      role="img"
      aria-label="Mission flow from JSON alerts through six agents into SQLite and Streamlit"
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
        const agent = ["coord", "collect", "classif", "correl", "eval", "report"].includes(node.id);
        return (
          <g key={node.id}>
            <rect
              x={node.x}
              y={node.y}
              width={nodeWidth}
              height={nodeHeight}
              rx={4}
              fill={agent ? theme.fill.tertiary : theme.bg.elevated}
              stroke={agent ? theme.accent.primary : theme.stroke.secondary}
            />
            <text
              x={node.x + nodeWidth / 2}
              y={node.y + 22}
              textAnchor="middle"
              fill={theme.text.primary}
              fontSize={11}
              fontFamily="ui-sans-serif, system-ui, sans-serif"
            >
              {labels[node.id]}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function SnippetBlock({ code }: { code: string }) {
  const theme = useHostTheme();
  return (
    <pre
      style={{
        margin: 0,
        padding: 12,
        overflow: "auto",
        whiteSpace: "pre",
        background: theme.bg.editor,
        color: theme.text.primary,
        border: `1px solid ${theme.stroke.tertiary}`,
        borderRadius: 6,
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
        fontSize: 12,
        lineHeight: 1.5,
      }}
    >
      {code}
    </pre>
  );
}

export default function TechStackReport() {
  const [side, setSide] = useCanvasState<Side>("side", "frontend");
  const [snippetId, setSnippetId] = useCanvasState("snippet", "chrome");
  const pool = SNIPPETS.filter((s) => s.side === side);
  const current = pool.find((s) => s.id === snippetId) ?? pool[0];

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>Observatoire SOC — frontend and backend</H1>
        <Text tone="secondary">
          Course project 420-VD2-ID. Two frontends sit on one Python backend:
          a Streamlit observatory on the GPU machine, and a static site on
          Vercel. The backend is six CrewAI roles, three tools, SQLite traces,
          and a local Qwen GGUF on llama-server.
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="2" label="Frontends: Streamlit and static HTML" />
        <Stat value="Three.js" label="Only authored browser library" />
        <Stat value="6" label="Backend agents, in order" />
        <Stat value=":8080" label="llama-server OpenAI API" tone="info" />
      </Grid>

      <Callout tone="info" title="React is not source code in this repo">
        You do not write React, Vue, Next.js, or an npm app. Streamlit's own
        browser client is a React app that the streamlit package ships, and
        it loads Plotly.js for charts. Your screens are Python calls
        (st.tabs, st.form, st.plotly_chart) plus dashboard/studio.css. The
        public site is HTML, CSS, assets/mark.js, and a short script in
        presentation.html.
      </Callout>

      <Stack gap={8}>
        <H2>How a mission crosses the two sides</H2>
        <Text tone="secondary" size="small">
          Backend boxes run in Python. The last box is the Streamlit frontend,
          which only reads SQLite and live_status.json. Accent boxes are the
          six roles. Source: pipeline/crew_runner.py.
        </Text>
        <PipelineMap />
      </Stack>

      <Divider />

      <Stack gap={12}>
        <H2>Frontend</H2>
        <Text>
          Two surfaces, both hand-written. The observatory runs only on the
          machine that has the model. Vercel serves the landing page and the
          slides, and .vercelignore keeps the dashboard, the database, and
          the GGUF off that deploy.
        </Text>

        <H3>What you write, and what the browser actually runs</H3>
        <Table
          headers={["Surface", "You write", "Browser runtime", "Where it is served"]}
          striped
          rows={[
            [
              "Observatory",
              "Python Streamlit + studio.css",
              "Streamlit client (React, shipped by the package) and Plotly.js",
              "localhost, streamlit run dashboard/app.py",
            ],
            [
              "Landing page",
              "index.html, inline CSS, assets/mark.js",
              "Browser plus Three.js 0.170.0 from unpkg",
              "Vercel, observatoire-soc-static.vercel.app",
            ],
            [
              "Slide deck",
              "presentation.html, inline CSS and JS",
              "Browser only. Scroll-snap, keyboard, wheel, touch",
              "Vercel /presentation",
            ],
          ]}
        />

        <H3>Observatory UI</H3>
        <Table
          headers={["Piece", "Pin or source", "Job in this app"]}
          striped
          rows={[
            ["Streamlit", "≥ 1.38", "Page, tabs, forms, buttons, sliders, file upload, dataframes, rerun"],
            ["session_state", "Streamlit", "focus_run, live_log, selected_dataset survive each rerun"],
            ["studio.css", "dashboard/studio.css", "Inter + Inter Tight, lime #d5f74c, hides Streamlit chrome"],
            [".streamlit/config.toml", "theme block", "primaryColor #d5f74c, background #eeeeee, text #111111"],
            ["Plotly", "≥ 5.24, Python API", "Graph, timeline, Sankey, comparison bars, heatmap"],
            ["Plotly.js", "bundled by Streamlit", "Draws those figures in the browser. Not imported by you"],
            ["NetworkX", "≥ 3.2", "Directed edges of the six agents, then Plotly plots the coordinates"],
            ["pandas", "≥ 2.2", "st.dataframe tables and the frames behind every chart"],
            ["Google Fonts", "Inter, Inter Tight", "Loaded from studio.css and from index.html"],
          ]}
        />

        <Grid columns={2} gap={16}>
          <Stack gap={8}>
            <H3>Tabs and widgets</H3>
            <Table
              headers={["Tab", "Controls"]}
              rows={[
                ["0. Mes sites", "Form, select, slider 1–5, dataframe, delete"],
                ["Datasets", "Table, picker, JSON and ZIP upload, schema expander"],
                ["1. Lancer", "Scenario or dataset select, start, live checklist"],
                ["2. Analyser", "Run picker, 4 metrics, replay slider, 5 charts"],
                ["3. Comparer", "8 KPIs, metric select, two runs side by side"],
                ["Guide", "How to launch, offline mode, what the charts mean"],
              ]}
            />
          </Stack>
          <Stack gap={8}>
            <H3>Charts</H3>
            <Table
              headers={["Function", "Mark"]}
              rows={[
                ["fig_agent_graph", "Scatter lines and markers"],
                ["fig_timeline", "px.bar, duration by step"],
                ["fig_sankey", "go.Sankey of agent handoffs"],
                ["fig_compare_agents", "px.bar, duration or tokens"],
                ["fig_heatmap", "px.imshow of agent by run"],
              ]}
            />
          </Stack>
        </Grid>

        <H3>Public site</H3>
        <Table
          headers={["Piece", "Detail"]}
          striped
          rows={[
            ["index.html", "Vanilla HTML and CSS. Fixed nav, backdrop blur, lime pills, no framework"],
            ["Fonts", "Inter and Inter Tight from fonts.googleapis.com"],
            ["Three.js", "0.170.0 via import map on unpkg. WebGLRenderer, RoundedBoxGeometry, RoomEnvironment"],
            ["mark.js", "Three meshes, MeshPhysicalMaterial, pointer parallax, reduced-motion stop"],
            ["presentation.html", "Full-viewport slides, Manrope, progress bar, dot nav"],
            ["Deck script", "goTo(), keydown, wheel lock, touch swipe. About 80 lines at the bottom of the file"],
            ["vercel.json", "cleanUrls, no trailing slash, X-Content-Type-Options nosniff, Referrer-Policy"],
            [".vercelignore", "Drops .venv, .env, .gguf, .streamlit, data/traces, and node_modules"],
          ]}
        />
        <Text tone="tertiary" size="small">
          Product colors on both frontends: background #eeeeee, ink #111111, accent #d5f74c.
          Source: dashboard/studio.css, .streamlit/config.toml, index.html, vercel.json.
        </Text>
      </Stack>

      <Divider />

      <Stack gap={12}>
        <H2>Backend</H2>
        <Text>
          One Python 3.12 process runs the mission. CrewAI does not support
          3.14, so scripts/setup.sh refuses any other version and builds the
          venv with uv. Inference is a separate llama-server process. Nothing
          in the backend calls a cloud model.
        </Text>

        <H3>Runtime</H3>
        <Table
          headers={["Layer", "Technology", "Job"]}
          striped
          rows={[
            ["Language", "Python 3.12", "Agents, tools, traces, dataset import, CLI"],
            ["Env", "uv + .venv", "Created by scripts/setup.sh from requirements.txt"],
            ["Config", "python-dotenv ≥ 1.0", "Loads .env: API base, GGUF path, GPU layers, context, port"],
            ["Agents", "CrewAI ≥ 0.80", "Agent, Task, Crew, Process.sequential, kickoff"],
            ["LLM adapter", "langchain-openai ≥ 0.2", "CrewAI LLM(model='openai/…', base_url=local)"],
            ["HTTP client", "openai ≥ 1.40", "Readiness check, direct chat, fallback if CrewAI fails"],
            ["Schemas", "Pydantic ≥ 2.7", "Used by CrewAI for structured agent IO"],
            ["HTTP / retry", "httpx ≥ 0.27, tenacity ≥ 8.3", "Client stack under OpenAI, CrewAI, and the hub"],
            ["Inference", "llama.cpp llama-server", "OpenAI /v1 on 127.0.0.1:8080, ./bin/llama-server"],
            ["Model", "Qwen3.6-35B-A3B Q3_K_M GGUF", "Heretic Cerebellum. Thinking template off. ~12 GB"],
            ["GPU", "N_GPU_LAYERS=30, CTX_SIZE=8192", "Tuned in .env for a 12 GB card. --jinja --parallel 1"],
            ["Download", "huggingface_hub ≥ 0.26", "scripts/download_model.sh, hf CLI and Python API"],
            ["Traces", "SQLite stdlib", "data/traces/observatory.db, tables runs and steps"],
            ["Live bridge", "JSON + threading.Lock", "data/traces/live_status.json, written every phase"],
            ["Tables for the UI", "pandas ≥ 2.2, numpy ≥ 1.26", "runs_df, steps_df, filters, kpi_dict"],
          ]}
        />

        <H3>Python packages</H3>
        <Text size="small" tone="secondary">
          Every direct dependency in <Code>requirements.txt</Code>. Streamlit,
          Plotly, and NetworkX are listed here because they are imported from
          Python, even though the pixels land in the frontend.
        </Text>
        <Table
          headers={["Package", "Pin", "Side", "Used for"]}
          striped
          rows={[
            ["crewai", "≥ 0.80.0", "Backend", "Agents, tasks, sequential crews, kickoff"],
            ["langchain-openai", "≥ 0.2.0", "Backend", "OpenAI-compatible LLM object inside CrewAI"],
            ["openai", "≥ 1.40.0", "Backend", "Chat completions against llama-server"],
            ["pydantic", "≥ 2.7.0", "Backend", "CrewAI structured models"],
            ["python-dotenv", "≥ 1.0.0", "Backend", "Load .env into config.py"],
            ["httpx", "≥ 0.27.0", "Backend", "HTTP under the OpenAI and hub clients"],
            ["tenacity", "≥ 8.3.0", "Backend", "Retries available to that client stack"],
            ["huggingface_hub", "≥ 0.26.0", "Backend", "Download the GGUF during setup"],
            ["pandas", "≥ 2.2.0", "Both", "Trace frames, KPIs, and st.dataframe"],
            ["numpy", "≥ 1.26.0", "Both", "Numeric backing for those frames"],
            ["streamlit", "≥ 1.38.0", "Frontend", "Observatory shell"],
            ["plotly", "≥ 5.24.0", "Frontend", "Every chart figure"],
            ["networkx", "≥ 3.2", "Frontend", "Agent graph topology"],
          ]}
        />

        <H3>Standard library the backend actually calls</H3>
        <Table
          headers={["Module", "Where", "Job"]}
          striped
          rows={[
            ["sqlite3", "pipeline/tracing.py", "runs and steps, row factory, one transaction per write"],
            ["json", "tools, traces, live status, datasets", "Alerts, inventory, live file, import payloads"],
            ["pathlib", "config.py and every loader", "ROOT, data/alerts, data/traces, models"],
            ["threading", "pipeline/live_status.py", "Lock around live_status.json"],
            ["uuid, datetime", "pipeline/tracing.py", "run_id and UTC timestamps"],
            ["dataclasses", "StepTrace, LLMResult, ValidationResult", "Step rows, token usage, import checks"],
            ["argparse", "scripts/run_scenario.py, run_batch.py", "CLI scenario, --offline, batch size"],
            ["zipfile, shutil, re", "pipeline/datasets.py", "ZIP import and dataset id checks"],
          ]}
        />

        <H3>Six roles and three tools</H3>
        <Grid columns={2} gap={16}>
          <Table
            headers={["Order", "Agent", "Job"]}
            columnAlign={["right", "left", "left"]}
            rows={[
              ["1", "Coordonnateur", "Split the mission into a short plan"],
              ["2", "Collecteur", "Summarize alerts and inventory"],
              ["3", "Classificateur", "Type, severity, likely false positives"],
              ["4", "Corrélateur", "Group alerts into campaigns"],
              ["5", "Évaluateur", "Check the rule scores, P1/P2/P3"],
              ["6", "Rapporteur", "Final brief for the analyst"],
            ]}
          />
          <Table
            headers={["Tool", "File", "Returns"]}
            rows={[
              ["parse_alert_log", "tools/alerts.py", "Alerts, severity and source counts"],
              ["lookup_asset_inventory", "tools/inventory.py", "Assets, criticality ≥ 4"],
              ["score_risk_rules", "tools/risk_rules.py", "Risk score and P1/P2/P3"],
            ]}
          />
        </Grid>
        <Text tone="tertiary" size="small">
          Roles live in config.AGENT_ROLES. tools/sites.py merges user-added
          hostnames into the same inventory before scoring, and can build a
          synthetic alert file aimed at those hostnames. Delegation is off on
          every agent.
        </Text>

        <H3>Scripts</H3>
        <Table
          headers={["Script", "Job"]}
          striped
          rows={[
            ["scripts/setup.sh", "Python 3.12 check, uv venv, pip install, .env, llama-server, GGUF"],
            ["scripts/install_llama_server.sh", "Place the llama.cpp binary in ./bin"],
            ["scripts/download_model.sh", "huggingface_hub download of the GGUF"],
            ["scripts/start_llm.sh", "llama-server with GPU layers, context, jinja"],
            ["scripts/run_scenario.py", "One mission. --offline skips the model and still runs the tools"],
            ["scripts/run_batch.py", "Repeated runs to fill the trace store"],
            ["scripts/export_traces.py", "Dump SQLite traces to JSON"],
          ]}
        />

        <H3>Data the backend reads</H3>
        <Table
          headers={["Store", "Path", "Shape"]}
          striped
          rows={[
            ["Lab alerts", "data/alerts/*.json", "Five scenarios, list of alert objects"],
            ["Inventory", "data/inventory/assets.json", "ACME-LAB assets, criticality 1–5"],
            ["User sites", "written by tools/sites.py", "Hostnames merged into the inventory"],
            ["Datasets", "data/datasets/<id>/", "manifest.json, alerts.json, optional assets.json"],
            ["Imports", "pipeline/datasets.py", "JSON or ZIP, validated before a mission can use them"],
            ["Traces", "data/traces/observatory.db", "runs and steps"],
            ["Demo seed", "data/traces/demo_runs.json", "Loaded by pipeline/seed.py so the UI is not empty"],
            ["Live file", "data/traces/live_status.json", "Current agent, phase, progress, latest output"],
          ]}
        />

        <H3>Built-in scenarios</H3>
        <Table
          headers={["Key", "Label", "Alert file"]}
          rows={[
            ["bruteforce_ssh", "Campagne brute-force SSH", "data/alerts/bruteforce_ssh.json"],
            ["phishing_creds", "Hameçonnage / vol d'identifiants", "data/alerts/phishing_creds.json"],
            ["ransomware_precursor", "Précurseurs ransomware", "data/alerts/ransomware_precursor.json"],
            ["noisy_ids", "Déferlement de faux positifs IDS", "data/alerts/noisy_ids.json"],
            ["exfiltration", "Exfiltration de données suspecte", "data/alerts/exfiltration.json"],
          ]}
        />
        <Text tone="tertiary" size="small">
          Source: config.SCENARIOS. An imported dataset or a user-site mission
          can run without being in that dict, as long as an alert file is passed
          to run_scenario.
        </Text>
      </Stack>

      <Divider />

      <Stack gap={12}>
        <H2>What SQLite does in this app</H2>
        <Text>
          SQLite is the memory of the observatory. It is a single file,
          data/traces/observatory.db, opened by Python's built-in sqlite3
          module. There is no database server, no Postgres, and no ORM.
          TraceStore in pipeline/tracing.py creates the file the first time
          a mission or the dashboard starts, then builds two tables if they
          are not already there.
        </Text>
        <Callout tone="info" title="SQLite is the history. The live pulse is a different file.">
          While a mission is running, the Lancer tab polls
          data/traces/live_status.json so the checklist can move. SQLite is
          written at the same moments, but the charts, the replay slider, the
          KPIs, and the run picker all read the database after each step is
          committed. Alert logs stay as JSON on disk. The GGUF is not stored
          here.
        </Callout>

        <H3>One mission, three writes</H3>
        <Table
          headers={["When", "Call", "What lands in the file"]}
          striped
          rows={[
            [
              "Before the first agent",
              "start_run",
              "One runs row, status running, with the scenario, mission text, and model name",
            ],
            [
              "After each of the six agents",
              "add_step",
              "One steps row: duration, tokens, tools, errors, quality, and the agent's text",
            ],
            [
              "After the rapporteur",
              "finish_run",
              "The same runs row is updated: success, partial, or failed, plus totals and the final brief",
            ],
          ]}
        />
        <Text>
          The run id looks like run_20261018T143022_ab12cd34. It is the primary
          key. Every step points back to it. A finished mission is one runs
          row and six steps rows. run_batch and the Streamlit launch button
          both go through SOCObservatoryCrew, so both write the same tables.
          Offline mode still writes them. The model being down does not skip
          the database.
        </Text>

        <H3>runs — one row per mission</H3>
        <Table
          headers={["Column", "Meaning"]}
          striped
          rows={[
            ["run_id", "Primary key. Timestamp plus 8 random hex characters"],
            ["scenario, scenario_label, mission", "Which case ran, and the French mission text"],
            ["started_at, ended_at", "UTC ISO timestamps. ended_at is filled in finish_run"],
            ["status", "running, then success, partial, or failed"],
            ["model", "Display name of the local GGUF"],
            ["total_duration_s", "Sum of the six step durations"],
            ["total_tokens_in, total_tokens_out", "Prompt and completion tokens, estimated when CrewAI does not return usage"],
            ["total_cost_usd", "From those token counts. Defaults to 0 because inference is local"],
            ["error_count, retry_count", "Tool failures and the CrewAI-to-OpenAI fallback"],
            ["quality_score", "0 to 0.98, from length and whether the brief mentions P1 or priority"],
            ["final_result", "The rapporteur brief, the text shown in Analyser"],
          ]}
        />

        <H3>steps — one row per agent</H3>
        <Table
          headers={["Column", "Meaning"]}
          striped
          rows={[
            ["id, run_id, step_index", "Auto id, foreign key to runs, order 0 through 5"],
            ["agent, task, status", "Role key, task title, success or error"],
            ["start_time, end_time, duration_s", "Wall clock for that agent only"],
            ["tokens_in, tokens_out, cost_usd", "That step's share of the run totals"],
            ["tools_used, tool_calls", "JSON text, for example parse_alert_log on the collecteur"],
            ["retries, errors", "errors is a JSON list of exception strings"],
            ["messages_to", "JSON list of the next agent, the edge the Sankey draws"],
            ["result_summary", "First 500 characters, used in the replay"],
            ["raw_output", "Full reply, stored only up to 8000 characters"],
            ["quality_score", "Same heuristic as the run, computed on this step's text"],
          ]}
        />
        <Text tone="secondary" size="small">
          tools_used, errors, and messages_to are TEXT columns. get_steps
          runs json.loads on them before the dashboard sees the row. A broken
          JSON value becomes an empty list instead of crashing the page.
        </Text>

        <H3>Who writes it, and who reads it</H3>
        <Table
          headers={["Piece", "Role"]}
          striped
          rows={[
            ["pipeline/tracing.py", "TraceStore. Opens the file, creates tables, inserts, updates, lists, exports"],
            ["pipeline/crew_runner.py", "The only writer during a mission: start_run, add_step, finish_run"],
            ["pipeline/seed.py", "If runs is empty, copies data/traces/demo_runs.json in so the first dashboard open is not blank"],
            ["dashboard/data_loader.py", "list_runs and get_steps become pandas frames. Every chart and KPI starts here"],
            ["dashboard/app.py", "Run picker, replay, comparison, and the final brief all use those frames"],
            ["scripts/export_traces.py", "export_json writes the whole database back out as demo-style JSON"],
            ["scripts/run_batch.py", "Many missions, same TraceStore, so Comparer has more than one run"],
          ]}
        />
        <Text>
          Each call opens a connection, sets row_factory to sqlite3.Row, commits,
          and closes. There is no pool and no background writer. The dashboard
          never sends SQL of its own. It asks TraceStore for dicts, and pandas
          does the averages: success rate, mean duration, token sums, the most
          used agent, and the slowest agent.
        </Text>
      </Stack>

      <Divider />

      <Stack gap={12}>
        <H2>How the backend talks to the frontend (MVT)</H2>
        <Text>
          Model, View, and Template share one Streamlit process. The Model
          keeps the rows. The View loads those rows and decides what to show.
          The Template draws the page. There is no second server and no JSON
          API between them.
        </Text>

        <Table
          headers={["Role", "Job", "Files in this project"]}
          striped
          rows={[
            [
              "Model",
              "Stores missions and the facts the agents used. Knows nothing about buttons or charts.",
              "pipeline/tracing.py, tools/, data/alerts, data/inventory",
            ],
            [
              "View",
              "Loads the Model, builds tables and figures, and starts a mission when a button is clicked.",
              "dashboard/app.py, dashboard/data_loader.py, dashboard/charts.py",
            ],
            [
              "Template",
              "Draws the page. Receives frames and figures. Never opens observatory.db.",
              "Streamlit widgets, dashboard/studio.css, Plotly.js in the browser",
            ],
          ]}
        />

        <H3>Model — pipeline/tracing.py</H3>
        <Text>
          This is the only SQL. list_runs and get_steps return dicts. The
          View calls them. The Template never does.
        </Text>
        <SnippetBlock
          code={`def list_runs(self) -> list[dict[str, Any]]:
    with self._conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

def get_steps(self, run_id: str) -> list[dict[str, Any]]:
    with self._conn() as conn:
        rows = conn.execute(
            "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
            (run_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for key in ("tools_used", "errors", "messages_to"):
            d[key] = json.loads(d[key] or "[]")
        out.append(d)
    return out`}
        />

        <H3>View reads the Model — dashboard/data_loader.py, dashboard/app.py</H3>
        <Text>
          runs_df and steps_df turn those dicts into frames. The Résultat tab
          then asks charts.py for figures and passes them to the Template.
        </Text>
        <SnippetBlock
          code={`def runs_df(store: TraceStore | None = None) -> pd.DataFrame:
    store = store or get_store()
    rows = store.list_runs()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)

def steps_df(store: TraceStore | None = None) -> pd.DataFrame:
    store = store or get_store()
    frames = []
    for run in store.list_runs():
        for s in store.get_steps(run["run_id"]):
            s = dict(s)
            s["scenario"] = run.get("scenario")
            frames.append(s)
    return pd.DataFrame(frames)

# dashboard/app.py — Résultat tab
runs = runs_df(store)
steps = steps_df(store)
run_meta = store.get_run(selected_run) or {}
run_steps = steps[steps["run_id"] == selected_run].sort_values("step_index")
chart(fig_agent_graph(active_agent=active), key="analyze_graph")
chart(fig_timeline(run_steps), key="analyze_timeline")
chart(fig_sankey(run_steps), key="analyze_sankey")`}
        />

        <H3>View writes the Model — dashboard/app.py, pipeline/crew_runner.py</H3>
        <Text>
          Démarrer calls run_scenario. The crew inserts the run, inserts one
          step per agent, and emits on_progress so the Template can update
          before the script finishes. focus_run is what the next rerun reads
          back from SQLite.
        </Text>
        <SnippetBlock
          code={`# pipeline/crew_runner.py
run_id = self.store.start_run(scenario_key, mission, model, scenario_label=meta.get("label"))
self.store.add_step(run_id, step_index, step)
self._emit(on_progress, {"state": "running", "agent": name, "progress": step_index / total_steps})

# dashboard/app.py
def on_progress(event: dict) -> None:
    prog = float(event.get("progress") or 0)
    msg = event.get("message") or ""
    placeholders["progress"].progress(min(max(prog, 0.02), 1.0), text=msg)
    with placeholders["graph"].container():
        live_chart(fig_agent_graph(active_agent=event.get("agent")))

result = crew.run_scenario(scenario, on_progress=on_progress, force_tools_only=use_offline)
if result:
    st.session_state.focus_run = result["run_id"]`}
        />

        <H3>Template — dashboard/app.py</H3>
        <Text>
          chart is the handoff. The View built the figure. This function only
          sends it to the browser. The metrics and the text area below read
          fields the View already pulled off the Model.
        </Text>
        <SnippetBlock
          code={`def chart(fig, key: str) -> None:
    st.plotly_chart(
        fig,
        width="stretch",
        key=key,
        config={"displayModeBar": False, "responsive": True},
    )

m1.metric("Statut", run_meta.get("status") or "—")
m2.metric("Qualité", run_meta.get("quality_score") or 0)
m3.metric("Durée", f"{round(float(run_meta.get('total_duration_s') or 0), 1)} s")
st.text_area("Ce que l'agent a produit", row.get("raw_output") or "")
st.write(run_meta.get("final_result") or "—")`}
        />

        <H3>The two paths, side by side</H3>
        <Table
          headers={["Path", "When", "What moves"]}
          striped
          rowTone={["info", "success", undefined]}
          rows={[
            [
              "Model → View → Template",
              "Every rerun of Analyser and Comparer",
              "SQLite rows → DataFrames → Plotly figures and tables",
            ],
            [
              "Template → View → Model",
              "Click on Démarrer",
              "Button → run_scenario → new runs and steps rows",
            ],
            [
              "View → Template, live",
              "During the six agents",
              "on_progress updates the checklist. live_status.json is the copy a refresh can still read.",
            ],
          ]}
        />
        <Text tone="secondary" size="small">
          The Vercel pages are a Template with no Model. index.html and
          presentation.html never call TraceStore. Only the Streamlit
          observatory is the MVT loop above.
        </Text>
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>Code that keeps each side running</H2>
        <Text tone="secondary">
          Shortened excerpts of the real files. Switch side, then pick a function.
        </Text>
        <Row gap={8}>
          <Pill
            active={side === "frontend"}
            onClick={() => {
              setSide("frontend");
              setSnippetId("chrome");
            }}
          >
            Frontend
          </Pill>
          <Pill
            active={side === "backend"}
            onClick={() => {
              setSide("backend");
              setSnippetId("kickoff");
            }}
          >
            Backend
          </Pill>
        </Row>
        <Row gap={8} wrap>
          {pool.map((s) => (
            <span key={s.id}>
              <Pill active={s.id === current.id} onClick={() => setSnippetId(s.id)}>
                {s.pill}
              </Pill>
            </span>
          ))}
        </Row>
        <Card>
          <CardHeader trailing={<Text size="small" tone="tertiary">{current.file}</Text>}>
            {current.title}
          </CardHeader>
          <CardBody>
            <Stack gap={12}>
              <Text>{current.why}</Text>
              <SnippetBlock code={current.code} />
            </Stack>
          </CardBody>
        </Card>
      </Stack>

      <Stack gap={8}>
        <H2>File map</H2>
        <Grid columns={2} gap={16}>
          <Stack gap={8}>
            <H3>Frontend</H3>
            <Table
              headers={["Path", "Job"]}
              rows={[
                ["dashboard/app.py", "Tabs, forms, launch, live log, replay"],
                ["dashboard/studio.css", "Visual chrome injected into the page"],
                ["dashboard/charts.py", "Plotly figures and the NetworkX graph"],
                ["dashboard/data_loader.py", "Pandas frames and kpi_dict"],
                [".streamlit/config.toml", "Streamlit theme tokens"],
                ["index.html", "Landing page"],
                ["assets/mark.js", "Three.js mark"],
                ["presentation.html", "Slide deck and its script"],
                ["vercel.json", "Static hosting headers"],
              ]}
            />
          </Stack>
          <Stack gap={8}>
            <H3>Backend</H3>
            <Table
              headers={["Path", "Job"]}
              rows={[
                ["config.py", "Paths, scenarios, roles, model defaults"],
                ["agents/factory.py", "CrewAI agents and the shared LLM"],
                ["pipeline/crew_runner.py", "SOCObservatoryCrew.run_scenario"],
                ["pipeline/llm.py", "Client, readiness, cost estimate"],
                ["pipeline/tracing.py", "SQLite TraceStore"],
                ["pipeline/live_status.py", "Live JSON for the UI"],
                ["pipeline/datasets.py", "Validate and import datasets"],
                ["pipeline/seed.py", "Demo traces"],
                ["tools/*.py", "Alerts, inventory, risk, user sites"],
                ["scripts/*.sh, scripts/*.py", "Setup, model, batch, export"],
              ]}
            />
          </Stack>
        </Grid>
      </Stack>
    </Stack>
  );
}
