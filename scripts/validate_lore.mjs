// Validates botanical_lore.json against the app (index.html).
// Run locally with:  node scripts/validate_lore.mjs
// Also runs automatically in CI on every push (see .github/workflows/validate.yml).
//
// FAILS the build (exit 1) when:
//   1. botanical_lore.json is not valid JSON.
//   2. Any lore entry is missing a required field or has an empty one.
//   3. Any learning target in the app's dropdown has no lore entry.
// WARNS (does not fail) when:
//   - A color anchor has no lore entry (expected for structural tissues).
//   - A lore entry matches no anchor and no dropdown target (possible typo).

import { readFileSync } from "node:fs";

const REQUIRED_FIELDS = ["proper_name", "analog", "intro_explanation", "beginner", "advanced"];
const errors = [];
const warnings = [];

// --- Load lore ---
let lore;
try {
  lore = JSON.parse(readFileSync("botanical_lore.json", "utf8"));
} catch (e) {
  console.error("FAIL: botanical_lore.json is not valid JSON —", e.message);
  process.exit(1);
}
const loreKeys = Object.keys(lore);

// --- Field completeness ---
for (const [key, entry] of Object.entries(lore)) {
  if (typeof entry !== "object" || entry === null) {
    errors.push(`Lore entry "${key}" is not an object.`);
    continue;
  }
  for (const f of REQUIRED_FIELDS) {
    const v = entry[f];
    if (v === undefined || v === null || String(v).trim() === "") {
      errors.push(`Lore entry "${key}" is missing or has an empty "${f}".`);
    }
  }
}

// --- Pull the app's tissue vocabulary out of index.html ---
const html = readFileSync("index.html", "utf8");

// dropdown learning targets: the <select id="objective-select"> option values
const objBlock = (html.match(/id="objective-select"[\s\S]*?<\/select>/) || [""])[0];
const targets = [...objBlock.matchAll(/value="([^"]+)"/g)].map(m => m[1]);

// color anchors: keys of the const colorAnchors = { ... } object
const anchorBlock = (html.match(/const colorAnchors\s*=\s*\{[\s\S]*?\};/) || [""])[0];
const anchors = [...anchorBlock.matchAll(/"([^"]+)"\s*:\s*\[/g)].map(m => m[1]);

if (targets.length === 0) errors.push("Could not find any objective-select targets in index.html.");
if (anchors.length === 0) errors.push("Could not find colorAnchors in index.html.");

// --- Every learning target MUST have lore (breaks the briefing otherwise) ---
for (const t of targets) {
  if (!loreKeys.includes(t)) {
    errors.push(`Dropdown target "${t}" has no entry in botanical_lore.json.`);
  }
}

// --- Anchors without lore: expected for structural tissues, informational only ---
for (const a of anchors) {
  if (!loreKeys.includes(a)) {
    warnings.push(`Color anchor "${a}" has no lore entry (structural/background — Rachel will use the generic fallback).`);
  }
}

// --- Lore entries reachable by nothing: likely a typo in the key ---
const vocab = new Set([...targets, ...anchors]);
for (const k of loreKeys) {
  if (!vocab.has(k)) {
    warnings.push(`Lore entry "${k}" matches no dropdown target and no color anchor — check for a typo in the key.`);
  }
}

// --- Report ---
console.log(`Checked ${loreKeys.length} lore entries, ${targets.length} dropdown targets, ${anchors.length} color anchors.`);
for (const w of warnings) console.log("WARN:", w);
if (errors.length) {
  for (const e of errors) console.error("FAIL:", e);
  process.exit(1);
}
console.log("OK: botanical_lore.json is valid and covers every learning target.");
