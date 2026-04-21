const data = await fetch("./data/demo-report.json").then((response) => response.json());

const summaryCopy = document.querySelector("#summary-copy");
const summaryStats = document.querySelector("#summary-stats");
const areaGroups = document.querySelector("#area-groups");
const missingList = document.querySelector("#missing-list");
const traceList = document.querySelector("#trace-list");

const grouped = groupByLocation(data.featuredFindings);

summaryCopy.textContent =
  `This sample run consolidated ${data.stats.mergedFindings} findings across ${data.stats.documents} source documents. ` +
  `${data.stats.conflicts} findings carried a conflict flag and ${data.stats.groundedRootCauses} findings retained a grounded root cause after validation.`;

summaryStats.innerHTML = [
  ["Merged findings", data.stats.mergedFindings],
  ["Conflict flags", data.stats.conflicts],
  ["Grounded causes", data.stats.groundedRootCauses],
  ["Missing locations", data.stats.missingLocations],
]
  .map(
    ([label, value]) => `
      <div class="summary-stat">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `,
  )
  .join("");

areaGroups.innerHTML = Object.entries(grouped)
  .map(
    ([location, findings]) => `
      <article class="area-card">
        <h3>${location}</h3>
        ${findings.map(renderFindingRow).join("")}
      </article>
    `,
  )
  .join("");

missingList.innerHTML = data.featuredFindings
  .flatMap((finding) => finding.conflicts)
  .slice(0, 6)
  .map((item) => `<div class="stack-item">${item}</div>`)
  .join("") || `<div class="stack-item">No missing or conflict notes were included in this sample slice.</div>`;

traceList.innerHTML = data.featuredFindings
  .slice(0, 6)
  .map((finding) => {
    const trace = finding.trace[0];
    if (!trace) {
      return `<div class="stack-item"><strong>${finding.id}</strong><div>No trace row available.</div></div>`;
    }
    return `<div class="stack-item"><strong>${finding.id}</strong><div>${trace.doc_type} page ${trace.page}: ${trace.snippet}</div></div>`;
  })
  .join("");

function renderFindingRow(finding) {
  const images = finding.images.length
    ? `<div class="finding-images">${finding.images
        .slice(0, 3)
        .map((src) => `<img src="${src}" alt="${finding.observation}">`)
        .join("")}</div>`
    : "";

  return `
    <div class="finding-row">
      <strong>${finding.observation}</strong>
      <p>${finding.reasoning}</p>
      <div class="finding-meta">
        <span class="meta-pill">${finding.severity} severity</span>
        <span class="meta-pill">${finding.confidence} confidence</span>
        <span class="meta-pill">${finding.id}</span>
      </div>
      <div class="finding-grid">
        <div class="finding-box">
          <h4>Root cause</h4>
          <p>${finding.rootCause}</p>
        </div>
        <div class="finding-box">
          <h4>Supporting reference</h4>
          <p>${renderReference(finding)}</p>
        </div>
        <div class="finding-box">
          <h4>Recommended actions</h4>
          <ul>${finding.actions.map((action) => `<li>${action}</li>`).join("")}</ul>
        </div>
        <div class="finding-box">
          <h4>Conflict note</h4>
          <p>${finding.conflicts[0] || "No conflict recorded for this finding."}</p>
        </div>
      </div>
      ${images}
    </div>
  `;
}

function renderReference(finding) {
  return finding.supportingReference
    .map((reference) => `${reference.docType} page ${reference.page}: ${reference.snippet}`)
    .join(" | ");
}

function groupByLocation(findings) {
  return findings.reduce((accumulator, finding) => {
    const key = finding.location;
    accumulator[key] ??= [];
    accumulator[key].push(finding);
    return accumulator;
  }, {});
}
