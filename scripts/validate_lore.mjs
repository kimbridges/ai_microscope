// Validates the slide manifests and the shared botanical lore.
// Run locally with:  node scripts/validate_lore.mjs
// Also runs in CI on every push (see .github/workflows/validate.yml).
//
// FAILS the build (exit 1) when:
//   1. A slide manifest is not valid JSON, or is missing required fields.
//   2. A tissue's color is not [r,g,b] with 0-255 integers, or pct is not a number.
//   3. Two tissues in a slide share the same color (identification would be ambiguous).
//   4. A referenced lore entry exists but is missing a required field / has an empty one.
// WARNS (does not fail) when:
//   - A tissue's lore key has no entry yet in botanical_lore.json (e.g. midrib,
//     pending a botanical write-up) — flagged so it isn't forgotten.

import { readFileSync, readdirSync, existsSync } from "node:fs";

const REQUIRED_LORE_FIELDS = ["proper_name", "analog", "intro_explanation", "beginner", "advanced"];
const errors = [];
const warnings = [];

// --- Shared lore ---
let lore = {};
try {
  lore = JSON.parse(readFileSync("botanical_lore.json", "utf8"));
} catch (e) {
  console.error("FAIL: botanical_lore.json is not valid JSON —", e.message);
  process.exit(1);
}

// --- Discover slide manifests (slide_*.json at repo root) ---
const slideFiles = readdirSync(".").filter(f => /^slide_.*\.json$/.test(f));
if (slideFiles.length === 0) errors.push("No slide manifest found (expected slide_*.json).");

const isRGB = (c) => Array.isArray(c) && c.length === 3 &&
  c.every(v => Number.isInteger(v) && v >= 0 && v <= 255);
const key = (c) => c.join(",");

for (const f of slideFiles) {
  let slide;
  try {
    slide = JSON.parse(readFileSync(f, "utf8"));
  } catch (e) {
    errors.push(`${f}: not valid JSON — ${e.message}`);
    continue;
  }
  for (const field of ["id", "image", "mask", "tissues"]) {
    if (!(field in slide)) errors.push(`${f}: missing "${field}".`);
  }
  if (slide.mask && !existsSync(slide.mask)) errors.push(`${f}: mask file "${slide.mask}" not found.`);
  if (slide.image && !existsSync(slide.image)) errors.push(`${f}: image file "${slide.image}" not found.`);
  if (!Array.isArray(slide.tissues)) continue;

  const seen = new Map();
  for (const t of slide.tissues) {
    const label = `${f} · tissue "${t.key || "?"}"`;
    if (!t.key) errors.push(`${label}: missing "key".`);
    if (!isRGB(t.color)) errors.push(`${label}: "color" must be [r,g,b] integers 0-255.`);
    if (typeof t.pct !== "number") errors.push(`${label}: "pct" must be a number.`);
    if (isRGB(t.color)) {
      if (seen.has(key(t.color)))
        errors.push(`${label}: color ${key(t.color)} duplicates "${seen.get(key(t.color))}" — ambiguous identification.`);
      seen.set(key(t.color), t.key);
    }
    if (t.lore) {
      const entry = lore[t.lore];
      if (!entry) {
        warnings.push(`${label}: lore key "${t.lore}" has no entry in botanical_lore.json yet.`);
      } else {
        for (const fld of REQUIRED_LORE_FIELDS) {
          if (entry[fld] === undefined || String(entry[fld]).trim() === "")
            errors.push(`${label}: lore "${t.lore}" is missing/empty "${fld}".`);
        }
      }
    } else {
      warnings.push(`${label}: no "lore" key set.`);
    }
  }
}

// --- Report ---
console.log(`Checked ${slideFiles.length} slide manifest(s) against botanical_lore.json.`);
for (const w of warnings) console.log("WARN:", w);
if (errors.length) {
  for (const e of errors) console.error("FAIL:", e);
  process.exit(1);
}
console.log("OK: slide manifests are valid and consistent with the lore.");
