const data = await fetch("./data/demo-report.json").then((response) => response.json());

const state = {
  findings: data.featuredFindings,
  filteredFindings: data.featuredFindings,
  selectedFindingId: data.featuredFindings[0]?.id ?? null,
  replayRunning: false,
};

const statsGrid = document.querySelector("#stats-grid");
const stagesList = document.querySelector("#stages-list");
const consoleLog = document.querySelector("#console-log");
const progressFill = document.querySelector("#progress-fill");
const progressLabel = document.querySelector("#progress-label");
const runDemoButton = document.querySelector("#run-demo");
const demoStatus = document.querySelector("#demo-status");
const demoStatusCopy = document.querySelector("#demo-status-copy");
const artifactsGrid = document.querySelector("#artifacts-grid");
const findingList = document.querySelector("#finding-list");
const detailCard = document.querySelector("#detail-card");
const locationFilter = document.querySelector("#location-filter");
const severityFilter = document.querySelector("#severity-filter");
const conflictFilter = document.querySelector("#conflict-filter");
const searchInput = document.querySelector("#search-input");
const severityBars = document.querySelector("#severity-bars");
const confidenceBars = document.querySelector("#confidence-bars");
const topAreaList = document.querySelector("#top-area-list");
const findingCardTemplate = document.querySelector("#finding-card-template");

const stageConsoleLabels = [
  "Loading inspection and thermal PDFs",
  "Building evidence payload with page and image references",
  "Tagging usable visual evidence against findings",
  "Grounding each claim to source references",
  "Normalizing terminology across report types",
  "Merging findings with content fingerprints",
  "Checking conflicts and missing fields",
  "Scoring confidence for each finding",
  "Running structured severity and cause logic",
  "Validating evidence boundaries before composition",
  "Composing the client-ready DDR output",
];

renderStats();
renderStages();
renderArtifacts();
renderFilterOptions();
renderDistributions();
applyFilters();
bindEvents();

function renderStats() {
  const statItems = [
    ["Source documents", data.stats.documents],
    ["Pages analyzed", data.stats.pages],
    ["Merged findings", data.stats.mergedFindings],
    ["Conflict flags", data.stats.conflicts],
  ];

  statsGrid.innerHTML = statItems
    .map(
      ([label, value]) => `
        <article class="stat-card">
          <span>${label}</span>
          <strong>${value}</strong>
        </article>
      `,
    )
    .join("");
}

function renderStages() {
  stagesList.innerHTML = data.stages
    .map(
      (stage) => `
        <article class="stage-card" data-step="${stage.step}">
          <span class="stage-step">${stage.step}</span>
          <h3>${stage.title}</h3>
          <p>${stage.detail}</p>
        </article>
      `,
    )
    .join("");
}

function renderArtifacts() {
  const cards = [
    {
      title: "Evidence-first",
      body: "The demo keeps claim grounding visible by linking findings back to document pages, snippets, and images.",
    },
    {
      title: "Rule-based reasoning",
      body: "Severity, conflicts, and root-cause gating stay deterministic so the report does not invent unsupported facts.",
    },
    {
      title: "Generalized flow",
      body: "The pipeline is framed around canonical findings rather than one fixed sample report layout.",
    },
    ...data.artifacts.map((artifact) => ({
      title: artifact.title,
      body: `${artifact.format} · ${artifact.description}`,
    })),
  ];

  artifactsGrid.innerHTML = cards
    .map(
      (card) => `
        <article class="principle-card">
          <h3>${card.title}</h3>
          <p>${card.body}</p>
        </article>
      `,
    )
    .join("");
}

function renderFilterOptions() {
  const locations = Array.from(new Set(data.featuredFindings.map((finding) => finding.location)));
  locationFilter.innerHTML = [
    `<option value="">All locations</option>`,
    ...locations.map((location) => `<option value="${location}">${location}</option>`),
  ].join("");
}

function renderDistributions() {
  renderBarGroup(severityBars, data.distribution.severity, data.stats.mergedFindings);
  renderBarGroup(confidenceBars, data.distribution.confidence, data.stats.mergedFindings);

  topAreaList.innerHTML = data.distribution.topAreas
    .map(
      ([area, count]) => `
        <div class="top-area-row">
          <span>${area}</span>
          <strong>${count}</strong>
        </div>
      `,
    )
    .join("");
}

function renderBarGroup(target, entries, total) {
  target.innerHTML = Object.entries(entries)
    .map(([key, value]) => {
      const width = Math.max((value / total) * 100, 6);
      return `
        <div class="bar-row">
          <span>${key}</span>
          <div class="bar-track">
            <div class="bar-fill" data-key="${key}" style="width:${width}%"></div>
          </div>
          <strong>${value}</strong>
        </div>
      `;
    })
    .join("");
}

function bindEvents() {
  runDemoButton.addEventListener("click", runReplay);
  [locationFilter, severityFilter, conflictFilter, searchInput].forEach((element) => {
    element.addEventListener("input", applyFilters);
    element.addEventListener("change", applyFilters);
  });
}

function applyFilters() {
  const searchValue = searchInput.value.trim().toLowerCase();
  const locationValue = locationFilter.value;
  const severityValue = severityFilter.value;
  const conflictValue = conflictFilter.value;

  state.filteredFindings = state.findings.filter((finding) => {
    const matchesSearch =
      !searchValue ||
      [finding.location, finding.observation, finding.normalizedObservation, finding.rootCause]
        .join(" ")
        .toLowerCase()
        .includes(searchValue);
    const matchesLocation = !locationValue || finding.location === locationValue;
    const matchesSeverity = !severityValue || finding.severity === severityValue;
    const matchesConflict = conflictValue !== "with-conflicts" || finding.conflicts.length > 0;
    return matchesSearch && matchesLocation && matchesSeverity && matchesConflict;
  });

  if (!state.filteredFindings.some((finding) => finding.id === state.selectedFindingId)) {
    state.selectedFindingId = state.filteredFindings[0]?.id ?? null;
  }

  renderFindingList();
  renderDetail();
}

function renderFindingList() {
  if (!state.filteredFindings.length) {
    findingList.innerHTML = `<div class="detail-empty">No findings match the current filters.</div>`;
    return;
  }

  findingList.innerHTML = "";
  state.filteredFindings.forEach((finding) => {
    const card = findingCardTemplate.content.firstElementChild.cloneNode(true);
    card.dataset.id = finding.id;
    if (finding.id === state.selectedFindingId) {
      card.classList.add("is-active");
    }
    card.querySelector(".badge").dataset.severity = finding.severity;
    card.querySelector(".finding-location").textContent = finding.location;
    card.querySelector(".finding-title").textContent = finding.observation;
    card.querySelector(".finding-subtitle").textContent = finding.reasoning;
    card.querySelector(".finding-meta").innerHTML = [
      `<span class="meta-pill">${finding.severity} severity</span>`,
      `<span class="meta-pill">${finding.confidence} confidence</span>`,
      `<span class="meta-pill">${finding.conflicts.length} conflict${finding.conflicts.length === 1 ? "" : "s"}</span>`,
    ].join("");
    card.addEventListener("click", () => {
      state.selectedFindingId = finding.id;
      renderFindingList();
      renderDetail();
    });
    findingList.appendChild(card);
  });
}

function renderDetail() {
  const finding = state.filteredFindings.find((item) => item.id === state.selectedFindingId);
  if (!finding) {
    detailCard.innerHTML = `<div class="detail-empty">Choose a finding to inspect the evidence trail.</div>`;
    return;
  }

  const imageStrip = finding.images.length
    ? `
      <div class="image-strip">
        ${finding.images.map((src) => `<img src="${src}" alt="${finding.observation}">`).join("")}
      </div>
    `
    : "";

  const conflictList = finding.conflicts.length
    ? `<ul class="detail-list">${finding.conflicts.map((item) => `<li>${item}</li>`).join("")}</ul>`
    : `<p>No conflicts were raised for this finding in the sample run.</p>`;

  const actionList = finding.actions.length
    ? `<ul class="detail-list">${finding.actions.map((item) => `<li>${item}</li>`).join("")}</ul>`
    : `<p>No recommended action was attached to this finding.</p>`;

  const traceRows = finding.trace.length
    ? finding.trace
        .map(
          (item) => `
            <div class="trace-row">
              <strong>${item.doc_type} · page ${item.page}</strong>
              <p>${item.snippet || "Snippet not available"}</p>
            </div>
          `,
        )
        .join("")
    : `<div class="trace-row"><strong>No trace rows available</strong><p>The demo keeps this state explicit instead of filling it with guessed references.</p></div>`;

  detailCard.innerHTML = `
    <div class="detail-top">
      <div>
        <div class="eyebrow">Selected finding</div>
        <h3>${finding.location}</h3>
        <p class="detail-observation">${finding.observation}</p>
        <div class="detail-chip-row">
          <span class="detail-chip">${finding.id}</span>
          <span class="detail-chip">${finding.severity} severity</span>
          <span class="detail-chip">${finding.confidence} confidence</span>
          <span class="detail-chip">${finding.rootCauseStatus.replaceAll("_", " ")}</span>
        </div>
      </div>
    </div>
    ${imageStrip}
    <div class="detail-grid">
      <section class="detail-block">
        <h4>Grounded conclusion</h4>
        <p>${finding.rootCause}</p>
      </section>
      <section class="detail-block">
        <h4>Evidence text</h4>
        <p>${finding.evidenceText}</p>
      </section>
      <section class="detail-block">
        <h4>Recommended actions</h4>
        ${actionList}
      </section>
      <section class="detail-block">
        <h4>Conflicts</h4>
        ${conflictList}
      </section>
    </div>
    <div class="trace-table">
      ${traceRows}
    </div>
  `;
}

async function runReplay() {
  if (state.replayRunning) {
    return;
  }
  state.replayRunning = true;
  runDemoButton.disabled = true;
  demoStatus.textContent = "Running";
  demoStatusCopy.textContent = "Replaying the sample pipeline with grounded checkpoints.";
  consoleLog.innerHTML = "";
  progressFill.style.width = "0%";
  progressLabel.textContent = `0 / ${data.stages.length} stages`;
  resetStageCards();

  for (const [index, stage] of data.stages.entries()) {
    const stageNode = document.querySelector(`.stage-card[data-step="${stage.step}"]`);
    stageNode?.classList.add("is-active");

    appendConsoleLine(`[${stage.step}] ${stageConsoleLabels[index] || stage.title}`);
    appendConsoleLine(
      `<span>OK</span> ${stage.detail}`,
    );

    await sleep(320);

    stageNode?.classList.remove("is-active");
    stageNode?.classList.add("is-complete");

    const percent = ((index + 1) / data.stages.length) * 100;
    progressFill.style.width = `${percent}%`;
    progressLabel.textContent = `${index + 1} / ${data.stages.length} stages`;
  }

  appendConsoleLine(`<span>DONE</span> Sample DDR ready with ${data.stats.mergedFindings} merged findings and ${data.stats.conflicts} conflict flags.`);
  demoStatus.textContent = "Complete";
  demoStatusCopy.textContent = "Replay finished. Use the findings explorer to inspect the grounded sample output.";
  state.replayRunning = false;
  runDemoButton.disabled = false;
}

function resetStageCards() {
  document.querySelectorAll(".stage-card").forEach((node) => {
    node.classList.remove("is-active", "is-complete");
  });
}

function appendConsoleLine(text) {
  const line = document.createElement("div");
  line.className = "console-line";
  line.innerHTML = text;
  consoleLog.appendChild(line);
  consoleLog.scrollTop = consoleLog.scrollHeight;
}

function sleep(duration) {
  return new Promise((resolve) => window.setTimeout(resolve, duration));
}
