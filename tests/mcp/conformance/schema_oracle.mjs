/** Validate protocol samples against the unmodified official dated JSON Schema. */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const [tools, samples] = process.argv.slice(2);
if (!tools || !samples || process.argv.length !== 4) {
  console.error("Usage: node schema_oracle.mjs TOOLS_PREFIX SAMPLES_JSON");
  process.exit(2);
}

const fixtures = fileURLToPath(new URL("../fixtures/", import.meta.url));
const metadata = JSON.parse(readFileSync(resolve(fixtures, "official_schema.source.json"), "utf8"));
const source = readFileSync(resolve(fixtures, "official_schema.json"));
const digest = createHash("sha256").update(source).digest("hex");
if (digest !== metadata.sha256) {
  throw new Error("Official schema snapshot checksum mismatch.");
}
const require = createRequire(resolve(tools, "package.json"));
const Ajv2020 = require("ajv/dist/2020.js").default;
const addFormats = require("ajv-formats");
const ajv = new Ajv2020({ strict: false, allErrors: true });
addFormats(ajv);
const schema = JSON.parse(source.toString("utf8"));
ajv.addSchema(schema, metadata.source);
const documents = JSON.parse(readFileSync(resolve(samples), "utf8").replace(/^\uFEFF/, ""));
if (!Array.isArray(documents) || documents.length === 0) {
  throw new Error("Samples must be a nonempty array of { definition, value } objects.");
}
const validators = new Map();
const results = documents.map((sample, index) => {
  if (!Object.hasOwn(schema.$defs, sample.definition)) {
    throw new Error(`Unknown official definition: ${sample.definition}`);
  }
  let validate = validators.get(sample.definition);
  if (!validate) {
    validate = ajv.compile({ $ref: `${metadata.source}#/$defs/${sample.definition}` });
    validators.set(sample.definition, validate);
  }
  const valid = validate(sample.value);
  return { index, definition: sample.definition, valid, errors: validate.errors };
});
process.stdout.write(`${JSON.stringify({ protocolVersion: metadata.protocolVersion, results })}\n`);
process.exitCode = results.every((result) => result.valid) ? 0 : 1;
