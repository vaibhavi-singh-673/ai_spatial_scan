const demo = {
  tier: "video",
  input: "demo / calibrated example",
  score: 100,
  readiness: "READY_WITH_CAVEATS",
  checks: [
    { name: "video_file_found", status: "PASS", details: { files: ["room_01_walkthrough.mp4"] } },
    { name: "frames_decoded", status: "PASS", details: { decoded_frames: 3 } },
    { name: "minimum_frame_count", status: "PASS", details: { decoded_frames: 3, minimum: 3 } },
    { name: "usable_resolution", status: "PASS", details: { width: 1440, height: 1080 } },
    { name: "metric_calibration_declared", status: "PASS", details: { scale_m_per_pixel: 0.01 } }
  ],
  recommendations: []
};

const qualitySample = {
  schema_version: "1.0",
  tier: "lidar",
  input: "sample reports / lidar capture",
  score: 100,
  readiness: "READY_WITH_CAVEATS",
  checks: [
    { name: "required_metadata", status: "PASS", details: { missing: [] } },
    { name: "camera_matrix", status: "PASS", details: { shape: [3, 3] } },
    { name: "depth_frames_decoded", status: "PASS", details: { decoded: 120, total: 120 } },
    { name: "confidence_coverage", status: "PASS", details: { with_confidence: 120 } },
    { name: "pose_coverage", status: "PASS", details: { with_pose: 120 } }
  ],
  recommendations: []
};

const roomSample = {
  schema_version: "1.0",
  tier: "lidar",
  input: "sample reports / room reconstruction",
  score: 100,
  readiness: "READY_WITH_CAVEATS",
  rooms: [{
    id: "room_01",
    name: "Living room",
    floor_area_m2: { value: 18.6 },
    ceiling_height_m: { value: 2.52 },
    walls: [{ value: 4.8 }, { value: 3.9 }, { value: 4.8 }, { value: 3.9 }]
  }],
  checks: [
    { name: "room_geometry", status: "PASS", details: { rooms: 1 } },
    { name: "measurement_intervals", status: "PASS", details: { measurements: 6 } },
    { name: "drift_diagnostic", status: "PASS", details: { loop_closure: false } }
  ],
  recommendations: ["Confirm measurements against laser/tape ground truth before submission."]
};

const benchmarkSample = {
  schema_version: "1.0",
  tier: "all",
  input: "sample reports / benchmark gates",
  score: 100,
  readiness: "READY_WITH_CAVEATS",
  checks: [
    { name: "lidar_ceiling_gate", status: "PASS", details: { max_error_m: 0.009, tolerance_m: 0.015 } },
    { name: "photo_footprint_gate", status: "PASS", details: { error_fraction: 0.06, tolerance_fraction: 0.08 } },
    { name: "video_footprint_gate", status: "PASS", details: { error_fraction: 0.026, tolerance_fraction: 0.03 } },
    { name: "repeatability", status: "PASS", details: { captures: 2 } },
    { name: "incumbent_comparison", status: "PASS", details: { shared_dimensions: 8, our_wins: 6, required_fraction: 0.7 } }
  ],
  recommendations: []
};

const photoSample = {
  schema_version: "1.0",
  tier: "photos",
  input: "sample reports / calibrated photo room",
  score: 100,
  readiness: "READY_WITH_CAVEATS",
  checks: [
    { name: "image_found", status: "PASS", details: { decoded_images: 4 } },
    { name: "room_view_count", status: "PASS", details: { recommended_range: [2, 8] } },
    { name: "usable_resolution", status: "PASS", details: { width: 3024, height: 4032 } },
    { name: "metric_calibration_declared", status: "PASS", details: { scale_m_per_pixel: 0.01 } }
  ],
  recommendations: []
};

const multiRoomSample = {
  tier: "lidar",
  input: "sample reports / multi-room reconstruction",
  score: 100,
  readiness: "READY_WITH_CAVEATS",
  rooms: [
    { name: "Living room", floor_area_m2: { value: 18.6 }, ceiling_height_m: { value: 2.52 }, walls: [{ value: 4.8 }, { value: 3.9 }] },
    { name: "Kitchen", floor_area_m2: { value: 11.2 }, ceiling_height_m: { value: 2.51 }, walls: [{ value: 3.7 }, { value: 3.0 }] },
    { name: "Bedroom", floor_area_m2: { value: 13.4 }, ceiling_height_m: { value: 2.50 }, walls: [{ value: 4.1 }, { value: 3.3 }] },
    { name: "Connector", floor_area_m2: { value: 4.1 }, ceiling_height_m: { value: 2.50 }, walls: [{ value: 2.2 }, { value: 1.8 }] }
  ],
  checks: [{ name: "room_geometry", status: "PASS", details: { rooms: 3 } }, { name: "loop_closure", status: "PASS", details: { applied: true } }],
  recommendations: ["Confirm room boundaries and openings against measured ground truth."]
};

const auditSample = {
  tier: "rubric",
  input: "benchmarks / submission audit",
  score: 20,
  readiness: "READY_FOR_COLLECTION",
  rubric: [
    { name: "walk_in", weight: 30, status: "BLOCKED", evidence: "0 real capture rows, 0 ground-truth rows", next_step: "Add real capture and laser/tape ground truth" },
    { name: "fix_loop", weight: 25, status: "REVIEW", evidence: "Measured fixture ablation exists; laser/tape accuracy delta absent", next_step: "Add laser/tape ground truth and record before/after gate values" },
    { name: "three_tier_accuracy", weight: 15, status: "BLOCKED", evidence: "No measured photo, video, or LiDAR rows", next_step: "Add all three measured tiers" },
    { name: "compliance", weight: 10, status: "PASS", evidence: "Matrix and source artifacts present", next_step: "Keep partial items explicit" },
    { name: "incumbent", weight: 10, status: "BLOCKED", evidence: "No incumbent export", next_step: "Preserve magicplan or Polycam export" },
    { name: "capture_route", weight: 5, status: "PASS", evidence: "Protocol and cold-run script present", next_step: "Record non-engineer install time" },
    { name: "process", weight: 5, status: "PASS", evidence: "CI and tests present", next_step: "Keep Git history auditable" }
  ],
  recommendations: ["Collect real benchmark evidence before claiming accuracy or selection readiness."]
};

const sampleReports = { video: demo, lidar: qualitySample, room: roomSample, photo: photoSample, benchmark: benchmarkSample, "multi-room": multiRoomSample, audit: auditSample };

const $ = (id) => document.getElementById(id);
const pretty = (value) => typeof value === "object" ? JSON.stringify(value) : String(value ?? "");

const walkthroughVideo = $("walkthrough-video");
const walkthroughSource = $("walkthrough-source");
$("video-room-select").addEventListener("change", (event) => {
  const room = event.target.value;
  const filename = room === "connector" ? "connector_walkthrough.mp4" : `${room}_walkthrough.mp4`;
  walkthroughSource.src = `../fixtures/video/${room}/${filename}`;
  walkthroughVideo.load();
});

function render(data) {
  const score = Number(data.score ?? 0);
  const readiness = String(data.readiness ?? data.status ?? "UNKNOWN").toUpperCase();
  const tier = String(data.tier ?? "unknown").toUpperCase();
  const checks = data.checks || [];
  const failed = checks.filter((check) => check.status !== "PASS");
  const rubric = data.rubric || [];
  $("tier-value").textContent = tier;
  $("readiness-value").textContent = readiness;
  const reviewState = readiness === "REVIEW" || readiness === "READY_FOR_COLLECTION";
  $("readiness-value").className = reviewState ? "status-review" : readiness.includes("READY") ? "status-ready" : "status-blocked";
  $("score-value").innerHTML = `${score}<span class="unit">/100</span>`;
  $("input-value").textContent = data.input || "loaded JSON";
  $("score-ring").textContent = score;
  $("score-meter").style.width = `${Math.max(0, Math.min(100, score))}%`;
  const needsReview = readiness === "REVIEW";
  $("score-caption").textContent = readiness === "READY_FOR_COLLECTION" ? "Infrastructure is ready; real benchmark evidence still needs to be collected." : needsReview ? "The capture is usable, but evidence is missing before an accuracy claim." : "Technical capture checks are in good shape.";
  $("status-note").textContent = needsReview ? "Review means the capture can be processed, but evidence is missing before an accuracy claim." : "Ready with caveats means technical checks passed; benchmark evidence still determines accuracy.";
  $("pass-count").textContent = checks.length - failed.length;
  $("fail-count").textContent = failed.length;
  $("check-count").textContent = `${checks.length} checks`;
  $("recommendation-text").textContent = data.recommendations?.[0] || "No immediate action required.";
  $("recommendation-source").textContent = failed[0]?.name?.replaceAll("_", " ") || "All gates clear";
  $("checks").innerHTML = checks.map((check) => {
    const pass = check.status === "PASS";
    return `<div class="check ${pass ? "check-pass" : "check-fail"}"><span class="check-icon">${pass ? "✓" : "!"}</span><span class="check-name">${check.name.replaceAll("_", " ")}<small class="check-detail">${pretty(check.details)}</small></span><span class="check-status">${check.status}</span></div>`;
  }).join("");
  const rooms = data.rooms || [];
  $("rooms-panel").classList.toggle("hidden", rooms.length === 0);
  $("rooms").innerHTML = rooms.map((room) => `<div class="room"><h3>${room.name || room.id}</h3><div class="room-row"><span>Floor area</span><strong>${room.floor_area_m2?.value ?? "-"} m²</strong></div><div class="room-row"><span>Ceiling</span><strong>${room.ceiling_height_m?.value ?? "-"} m</strong></div><div class="room-row"><span>Walls</span><strong>${room.walls?.length ?? 0}</strong></div></div>`).join("");
  $("updated-value").textContent = `Loaded ${tier.toLowerCase()} report`;
  $("rubric-panel").classList.toggle("hidden", rubric.length === 0);
  $("rubric-score").textContent = `${data.score ?? 0} / 100 verified`;
  $("rubric-items").innerHTML = rubric.map((item) => {
    const status = String(item.status || "REVIEW").toLowerCase();
    return `<div class="rubric-item"><span class="rubric-name">${item.name.replaceAll("_", " ")} <small>(${item.weight}%)</small><span class="rubric-detail">${item.evidence}<br><b>Next:</b> ${item.next_step}</span></span><span class="rubric-status rubric-${status}">${item.status}</span></div>`;
  }).join("");
}

async function loadFile(file) { render(JSON.parse(await file.text())); }
$("file-input").addEventListener("change", (event) => { if (event.target.files[0]) loadFile(event.target.files[0]); });
$("demo-button").addEventListener("click", () => render(demo));
$("load-sample-button").addEventListener("click", () => render(sampleReports[$("sample-select").value]));
render(demo);