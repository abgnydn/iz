/**
 * iz-1 browser inference + per-facility .flora adapter loader.
 *
 * Wires:
 *   1. Transformers.js ONNX Runtime WebGPU for the base ViT (Pass 3 v0)
 *   2. iz.flora v2 multi-layer adapter format (from ../fused-lora/lora-adapter.ts spec)
 *   3. Custom fused WGSL LoRA kernels (lora_down + lora_up + adam_lora) — to be ported
 *      from ~/Documents/GitHub/fused-lora/src/compiler/shaders/ into this bundle.
 *
 * v0: stub — runs a synthetic prediction from the tabular feature vector while
 * the ONNX/WGSL plumbing is being wired. The UI contract is locked so the
 * backend swap is invisible to the user.
 */

const $ = (id: string) => document.getElementById(id) as HTMLElement;

interface FacilityPriors {
  cbam_scope: string;
  baseline_co2_t_month: number;   // sector default × capacity
  no2_to_co2_slope: number;       // rough conversion until iz-1 ships
}

const FACILITY_PRIORS: Record<string, FacilityPriors> = {
  "akcansa-buyukcekmece": { cbam_scope: "cement", baseline_co2_t_month: 244_125, no2_to_co2_slope: 8.5e7 },
  "cimsa-mersin":         { cbam_scope: "cement", baseline_co2_t_month: 130_200, no2_to_co2_slope: 8.5e7 },
  "erdemir-eregli":       { cbam_scope: "steel",  baseline_co2_t_month: 577_433, no2_to_co2_slope: 1.2e8 },
  "tosyali-osmaniye":     { cbam_scope: "steel",  baseline_co2_t_month: 144_375, no2_to_co2_slope: 9.0e7 },
};

const STATE: {
  modelLoaded: boolean;
  flora?: { layers: number; bytes: number };
} = { modelLoaded: false };

async function loadModelStub(): Promise<void> {
  // TODO: load ONNX-exported iz-1 base via Transformers.js v4 + WebGPU
  //   import { pipeline } from '@xenova/transformers';
  //   const reg = await pipeline('regression', 'abgnydn/iz-1', { device: 'webgpu' });
  //
  // Compile + cache custom WGSL fused-lora kernels here.
  await new Promise((r) => setTimeout(r, 50));
  STATE.modelLoaded = true;
}

async function parseFlora(file: File): Promise<{ layers: number; bytes: number }> {
  const buf = new Uint8Array(await file.arrayBuffer());
  if (buf.length < 32 || buf[0] !== 0x46 || buf[1] !== 0x4c || buf[2] !== 0x52 || buf[3] !== 0x41) {
    throw new Error("not a .flora file (missing FLRA magic)");
  }
  const dv = new DataView(buf.buffer);
  const version = dv.getUint32(4, true);
  // v1 = single layer; v2 (TBD in fused-lora) = multi-layer
  return { layers: version, bytes: buf.length };
}

function predictStub(facilityId: string, no2Override?: number): number {
  const p = FACILITY_PRIORS[facilityId];
  if (!p) return 0;
  const no2 = no2Override ?? 5e-5;  // typical TR cement plant column density
  const delta = p.no2_to_co2_slope * (no2 - 3e-5);
  return Math.max(0, p.baseline_co2_t_month * 0.65 + delta * 0.5);
}

async function predict() {
  const fid = (document.getElementById("facility-select") as HTMLSelectElement).value;
  const monthEl = document.getElementById("month-input") as HTMLInputElement;
  const no2El = document.getElementById("no2-input") as HTMLInputElement;
  const floraEl = document.getElementById("flora-input") as HTMLInputElement;

  if (!STATE.modelLoaded) await loadModelStub();

  if (floraEl.files && floraEl.files[0]) {
    try {
      STATE.flora = await parseFlora(floraEl.files[0]);
    } catch (e) {
      $("meta").textContent = `.flora parse error: ${(e as Error).message}`;
      return;
    }
  }

  const no2 = no2El.value ? parseFloat(no2El.value) * 1e-6 : undefined;
  const co2 = predictStub(fid, no2);
  const ann = co2 * 12;
  $("result").textContent = `${co2.toLocaleString(undefined, { maximumFractionDigits: 0 })} tCO₂ / month  (~${ann.toLocaleString(undefined, { maximumFractionDigits: 0 })} t/yr)`;

  const lines = [
    `facility:       ${fid}`,
    `month:          ${monthEl.value}`,
    `no2_override:   ${no2 ?? "auto"}`,
    `model:          iz-1 v0 (stub — ONNX bundle pending Pass 2 export)`,
    `flora:          ${STATE.flora ? `loaded, v${STATE.flora.layers}, ${STATE.flora.bytes} bytes` : "none (using base)"}`,
    `runtime:        Transformers.js + WebGPU (planned) — current stub is JS-only`,
  ];
  $("meta").textContent = lines.join("\n");
}

(document.getElementById("predict-btn") as HTMLButtonElement).addEventListener("click", predict);
loadModelStub().then(() => { $("meta").textContent = "model loaded (stub)"; });
